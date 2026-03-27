"""Zero-Copy Canvas Renderer — design/weave/fabric modları, Point Paper grid, araç önizlemeleri."""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QImage, QPainter, QColor, QPen, qRgb, QTransform
from PySide6.QtCore import Qt, QRectF
import numpy as np

from tcad.tools import bresenham_line, flood_fill
from tcad.domain import PatchCommand


class PatternItem(QGraphicsItem):
    """Zero-Copy matris nesnesi. Raporlama için tek imajı maliyetsiz çoğaltır."""

    def __init__(self, view):
        super().__init__()
        self.view = view

    def boundingRect(self):
        doc = self.view.doc
        return QRectF(0, 0,
                      doc.width * doc.repeat_x,
                      doc.height * doc.repeat_y)

    def paint(self, painter, option, widget):
        doc = self.view.doc
        if not self.view.qimage:
            return

        img_w = self.view.qimage.width()
        img_h = self.view.qimage.height()

        rect = option.exposedRect
        l = max(0, int(rect.left() // max(img_w, 1)))
        r = min(doc.repeat_x - 1, int(rect.right() // max(img_w, 1)))
        t = max(0, int(rect.top() // max(img_h, 1)))
        b = min(doc.repeat_y - 1, int(rect.bottom() // max(img_h, 1)))

        for rx in range(l, r + 1):
            for ry in range(t, b + 1):
                painter.setOpacity(1.0 if (rx == 0 and ry == 0) else 0.4)
                painter.drawImage(rx * img_w, ry * img_h, self.view.qimage)


class CanvasView(QGraphicsView):
    """Ana tuval — sonsuz pan/zoom, araç yönetimi, Zero-Copy render."""

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.gfx_scene = QGraphicsScene(self)
        self.setScene(self.gfx_scene)

        self.setRenderHint(QPainter.Antialiasing, False)
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)

        self.item = PatternItem(self)
        self.gfx_scene.addItem(self.item)

        self.qimage = None
        self.grid_ref = None

        self.zoom = 1.0
        self._space_held = False
        self._mid_panning = False
        self._pan_last = None

        # Tool state
        self.is_drawing = False
        self.stroke_start = None
        self.preview_pos = None
        self.temp_min_x = 0
        self.temp_max_x = 0
        self.temp_min_y = 0
        self.temp_max_y = 0
        self.old_grid_backup = None

        # Selection state
        self.selection_rect = None
        self.floating_patch = None
        self.floating_pos = None

    @property
    def doc(self):
        return self.mw.doc

    # ── Render ──────────────────────────────────────────────

    def rebuild_qimage(self):
        v_mode = getattr(self.doc, 'view_mode', 'design')

        if (v_mode == 'fabric'
                and getattr(self.doc, 'fabric_rgb', None) is not None):
            self.grid_ref = self.doc.fabric_rgb
            h, w, _ = self.grid_ref.shape
            bpl = w * 4
            self.qimage = QImage(self.grid_ref.data, w, h, bpl,
                                 QImage.Format_RGBX8888)

        elif (v_mode == 'weave'
              and getattr(self.doc, 'lift_plan', None) is not None):
            self.grid_ref = self.doc.lift_plan
            h, w = self.grid_ref.shape
            bpl = self.grid_ref.strides[0]
            self.qimage = QImage(self.grid_ref.data, w, h, bpl,
                                 QImage.Format_Indexed8)
            table = [qRgb(255, 255, 255), qRgb(0, 0, 0)]
            for _ in range(254):
                table.append(qRgb(128, 128, 128))
            self.qimage.setColorTable(table)

        else:
            self.grid_ref = self.doc.grid
            h, w = self.grid_ref.shape
            bpl = self.grid_ref.strides[0]
            self.qimage = QImage(self.grid_ref.data, w, h, bpl,
                                 QImage.Format_Indexed8)
            self.update_palette()

        self.gfx_scene.setSceneRect(self.item.boundingRect())
        
        # --- Kırmızı Takım: 3D Kumaş Fiziksel Sıklık Oranı (Aspect Ratio) ---
        if v_mode == 'fabric':
            # Kumaş simülasyonunda iplik yoğunluklarına göre QTransform uygula
            # X Ekseninde Çözgü Kalınlığı = 1/epc | Y Ekseninde Atkı Kalınlığı = 1/ppc
            # Bağıl oran = (1/epc) / (1/ppc) = ppc / epc
            scale_y = getattr(self.doc, 'epc', 40) / max(1, getattr(self.doc, 'ppc', 40))
            self.item.setTransform(QTransform().scale(1.0, scale_y))
            # Transform uygulandıktan sonra Sahne Sınırlarını genişlet
            self.gfx_scene.setSceneRect(self.item.mapRectToScene(self.item.boundingRect()))
        else:
            self.item.setTransform(QTransform())  # Sıfırla
            self.gfx_scene.setSceneRect(self.item.boundingRect())
            
        self.gfx_scene.update()

    def update_palette(self):
        if self.qimage is None:
            return
        table = []
        if self.doc.is_technical:
            table.append(qRgb(255, 255, 255))
            for _ in range(1, 256):
                table.append(qRgb(0, 0, 0))
        else:
            for r, g, b in self.doc.palette:
                table.append(qRgb(r, g, b))
        self.qimage.setColorTable(table)
        self.gfx_scene.update()

    def update_region(self, x, y, w, h):
        self.doc.is_dirty = True
        self.gfx_scene.update(x, y, w, h)
        for rx in range(self.doc.repeat_x):
            for ry in range(self.doc.repeat_y):
                if rx > 0 or ry > 0:
                    self.gfx_scene.update(
                        rx * self.doc.width + x,
                        ry * self.doc.height + y, w, h)

    # ── Foreground Overlays ─────────────────────────────────

    def drawForeground(self, painter, rect):
        l, r = int(rect.left()), int(rect.right()) + 1
        t, b = int(rect.top()), int(rect.bottom()) + 1

        w_tot = self.doc.width * self.doc.repeat_x
        h_tot = self.doc.height * self.doc.repeat_y

        # Point Paper Grid
        if self.zoom > 5:
            painter.setRenderHint(QPainter.Antialiasing, False)
            major = QPen(QColor(255, 50, 50, 180), 0)
            minor = QPen(QColor(150, 150, 150, 100), 0)

            for x in range(max(0, l), min(w_tot, r)):
                painter.setPen(major if x % 8 == 0 else minor)
                painter.drawLine(x, max(0, t), x, min(h_tot, b))
            for y in range(max(0, t), min(h_tot, b)):
                painter.setPen(major if y % 8 == 0 else minor)
                painter.drawLine(max(0, l), y, min(w_tot, r), y)

        # Makine Bölme Sınırları (Multi-head / Sectional Splits)
        if getattr(self.doc, 'hook_count', 0) > 0 and w_tot > self.doc.hook_count:
            painter.setPen(QPen(QColor(0, 255, 255, 200), 2, Qt.DashLine))
            splits = w_tot // self.doc.hook_count
            for i in range(1, splits + 1):
                sx = i * self.doc.hook_count
                if l <= sx <= r:
                    painter.drawLine(sx, max(0, t), sx, min(h_tot, b))

        # Tool Previews
        if (self.is_drawing and self.mw.active_tool in ['line', 'rect']
                and self.stroke_start and self.preview_pos):
            painter.setPen(QPen(QColor(255, 255, 255), 0, Qt.DashLine))
            px, py = self.stroke_start
            cx, cy = self.preview_pos
            if self.mw.active_tool == 'line':
                painter.drawLine(px, py, cx, cy)
            elif self.mw.active_tool == 'rect':
                painter.drawRect(min(px, cx), min(py, cy),
                                 abs(cx - px), abs(cy - py))

        # Selection Rect
        if self.selection_rect:
            painter.setPen(QPen(Qt.yellow, 0, Qt.DashLine))
            painter.drawRect(self.selection_rect)

        # Floating Patch
        if self.floating_patch is not None:
            fh, fw = self.floating_patch.shape
            img = QImage(self.floating_patch.data, fw, fh, fw,
                         QImage.Format_Indexed8)
            if self.qimage:
                img.setColorTable(self.qimage.colorTable())
            fx, fy = self.floating_pos
            painter.drawImage(fx, fy, img)
            painter.setPen(QPen(Qt.cyan, 0, Qt.DotLine))
            painter.drawRect(fx, fy, fw, fh)

        # Validation Errors
        v_mode = getattr(self.doc, 'view_mode', 'design')
        if v_mode in ('weave', 'fabric') and self.doc.float_errors:
            painter.setPen(Qt.NoPen)
            for err in self.doc.float_errors:
                x, y, length, d = err['x'], err['y'], err['len'], err['dir']
                if d == 'point':
                    painter.setBrush(QColor(255, 165, 0, 200))
                    if rect.intersects(QRectF(x, y, 1, 1)):
                        painter.drawRect(x, y, 1, 1)
                elif d in ('edge_x', 'edge_y'):
                    painter.setBrush(QColor(255, 0, 255, 180))
                    ew = length if d == 'edge_x' else 1
                    eh = length if d == 'edge_y' else 1
                    if rect.intersects(QRectF(x, y, ew, eh)):
                        painter.drawRect(x, y, ew, eh)
                else:
                    painter.setBrush(QColor(255, 0, 0, 180))
                    ew = length if d == 'weft' else 1
                    eh = length if d == 'warp' else 1
                    if rect.intersects(QRectF(x, y, ew, eh)):
                        painter.drawRect(x, y, ew, eh)

    # ── Input ───────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._space_held = True
            self.setCursor(Qt.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_fac = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.zoom *= zoom_fac
            self.scale(zoom_fac, zoom_fac)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        # Middle button pan
        if event.button() == Qt.MiddleButton:
            self._mid_panning = True
            self._pan_last = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            return

        # Space + left click pan
        if self._space_held and event.button() == Qt.LeftButton:
            self._mid_panning = True
            self._pan_last = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            return

        # Safety lock for non-design modes
        if getattr(self.doc, 'view_mode', 'design') != 'design':
            self.mw.status.showMessage(
                "TEKNİK GÖRÜNÜM: Çizim yapılamaz! Desen moduna geçin.")
            return

        pos = self.mapToScene(event.position().toPoint())
        x = int(pos.x()) % self.doc.width
        y = int(pos.y()) % self.doc.height

        if event.button() == Qt.LeftButton:
            tool = self.mw.active_tool
            color = self.mw.active_color

            if self.floating_patch is not None:
                self.commit_floating()
                return

            if tool == 'select':
                self.selection_rect = QRectF(x, y, 0, 0)
                self.stroke_start = (x, y)
                self.gfx_scene.update()

            elif tool == 'fill':
                target = self.doc.grid[y, x]
                mask, bbox = flood_fill(self.doc.grid, x, y, target, color)
                if mask is not None:
                    mx, my, mw, mh = bbox
                    old_p = self.doc.grid[my:my + mh, mx:mx + mw].copy()
                    new_p = old_p.copy()
                    new_p[mask[my:my + mh, mx:mx + mw]] = color
                    self.doc.grid[my:my + mh, mx:mx + mw] = new_p
                    self.mw.history.push(PatchCommand(
                        self.doc, mx, my, old_p, new_p, self.update_region))
                    self.update_region(mx, my, mw, mh)

            elif tool in ('pencil', 'eraser', 'line', 'rect'):
                self.is_drawing = True
                self.stroke_start = (x, y)
                self.preview_pos = (x, y)
                if tool in ('pencil', 'eraser'):
                    self.temp_min_x = self.temp_max_x = x
                    self.temp_min_y = self.temp_max_y = y
                    self.old_grid_backup = self.doc.grid.copy()
                    self._plot(x, y, color if tool == 'pencil' else 0)

    def mouseMoveEvent(self, event):
        # Pan handling
        if self._mid_panning and self._pan_last is not None:
            delta = event.position() - self._pan_last
            self._pan_last = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            return

        pos = self.mapToScene(event.position().toPoint())
        x = int(pos.x()) % self.doc.width
        y = int(pos.y()) % self.doc.height
        self.mw.status.showMessage(
            f"X: {x} | Y: {y} | Zoom: {self.zoom:.1f}x")

        if self.selection_rect and self.mw.active_tool == 'select':
            sx, sy = self.stroke_start
            self.selection_rect = QRectF(
                min(sx, x), min(sy, y), abs(x - sx), abs(y - sy))
            self.gfx_scene.update()
            return

        if self.is_drawing:
            tool = self.mw.active_tool
            color = self.mw.active_color if tool != 'eraser' else 0
            if tool in ('line', 'rect'):
                self.preview_pos = (x, y)
                self.gfx_scene.update()
            elif tool in ('pencil', 'eraser'):
                for px, py in bresenham_line(
                        self.preview_pos[0], self.preview_pos[1], x, y):
                    self._plot(px, py, color)
                self.preview_pos = (x, y)

    def mouseReleaseEvent(self, event):
        if (event.button() in (Qt.MiddleButton, Qt.LeftButton)
                and self._mid_panning):
            self._mid_panning = False
            self._pan_last = None
            self.setCursor(Qt.ArrowCursor)
            return

        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            tool = self.mw.active_tool
            color = self.mw.active_color

            if (tool in ('line', 'rect')
                    and self.stroke_start and self.preview_pos):
                x0, y0 = self.stroke_start
                x1, y1 = self.preview_pos
                mx, mX = min(x0, x1), max(x0, x1)
                my, mY = min(y0, y1), max(y0, y1)
                if mX == mx:
                    mX = mx + 1
                if mY == my:
                    mY = my + 1

                old_p = self.doc.grid[my:mY + 1, mx:mX + 1].copy()
                new_p = old_p.copy()

                if tool == 'line':
                    for px, py in bresenham_line(x0, y0, x1, y1):
                        if 0 <= py - my < new_p.shape[0] and 0 <= px - mx < new_p.shape[1]:
                            new_p[py - my, px - mx] = color
                elif tool == 'rect':
                    new_p[0, :] = color
                    new_p[-1, :] = color
                    new_p[:, 0] = color
                    new_p[:, -1] = color

                self.doc.grid[my:mY + 1, mx:mX + 1] = new_p
                self.mw.history.push(PatchCommand(
                    self.doc, mx, my, old_p, new_p, self.update_region))
                self.update_region(mx, my, mX - mx + 1, mY - my + 1)

            elif tool in ('pencil', 'eraser'):
                mx, mX = self.temp_min_x, self.temp_max_x
                my, mY = self.temp_min_y, self.temp_max_y
                old_p = self.old_grid_backup[my:mY + 1, mx:mX + 1].copy()
                new_p = self.doc.grid[my:mY + 1, mx:mX + 1].copy()
                self.mw.history.push(PatchCommand(
                    self.doc, mx, my, old_p, new_p, self.update_region))
                self.old_grid_backup = None

    def _plot(self, x, y, c):
        if 0 <= x < self.doc.width and 0 <= y < self.doc.height:
            self.doc.grid[y, x] = c
            self.temp_min_x = min(self.temp_min_x, x)
            self.temp_max_x = max(self.temp_max_x, x)
            self.temp_min_y = min(self.temp_min_y, y)
            self.temp_max_y = max(self.temp_max_y, y)
            self.update_region(x, y, 1, 1)

    # ── Selection & Float ───────────────────────────────────

    def exec_copy(self):
        if self.selection_rect:
            x, y = int(self.selection_rect.x()), int(self.selection_rect.y())
            w, h = int(self.selection_rect.width()), int(self.selection_rect.height())
            if w > 0 and h > 0:
                self.mw.clipboard = self.doc.grid[y:y + h, x:x + w].copy()
            self.selection_rect = None
            self.gfx_scene.update()

    def exec_paste(self):
        if hasattr(self.mw, 'clipboard') and self.mw.clipboard is not None:
            self.floating_patch = self.mw.clipboard.copy()
            self.floating_pos = (0, 0)
            self.mw.set_tool('select')
            self.gfx_scene.update()

    def commit_floating(self):
        if self.floating_patch is not None:
            fx, fy = self.floating_pos
            h, w = self.floating_patch.shape
            x_st, y_st = max(0, fx), max(0, fy)
            x_ed = min(self.doc.width, fx + w)
            y_ed = min(self.doc.height, fy + h)
            if x_ed > x_st and y_ed > y_st:
                old_p = self.doc.grid[y_st:y_ed, x_st:x_ed].copy()
                self.doc.grid[y_st:y_ed, x_st:x_ed] = \
                    self.floating_patch[y_st - fy:y_ed - fy,
                                        x_st - fx:x_ed - fx]
                new_p = self.doc.grid[y_st:y_ed, x_st:x_ed].copy()
                self.mw.history.push(PatchCommand(
                    self.doc, x_st, y_st, old_p, new_p, self.update_region))
                self.update_region(x_st, y_st, x_ed - x_st, y_ed - y_st)
            self.floating_patch = None
            self.gfx_scene.update()
