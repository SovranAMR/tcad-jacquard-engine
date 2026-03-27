"""Ana pencere — Menü, Toolbar, 3-yönlü görünüm, Autosave/Recovery."""

import os
import tempfile

from PySide6.QtWidgets import (QMainWindow, QToolBar, QFileDialog,
                                QMessageBox, QStatusBar)
from PySide6.QtGui import QAction, QUndoStack
from PySide6.QtCore import Qt, QTimer

from tcad.domain import Document
from tcad.fileio import save_project, load_project, import_image, export_png, import_jc5
from tcad.canvas import CanvasView
from tcad.panels import PalettePanel, PropsPanel
from tcad.cam_panel import CamPanel
from tcad.thread_panel import ThreadPanel


class MainWindow(QMainWindow):
    """Jacquard CAD Professional — Ana uygulama kabuğu."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jacquard CAD Professional")

        self.doc = Document(200, 200)
        self.history = QUndoStack(self)
        self.active_tool = 'pencil'
        self.active_color = 1
        self.clipboard = None

        # Canvas
        self.canvas = CanvasView(self)
        self.setCentralWidget(self.canvas)

        # Panels
        self.pal_panel = PalettePanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.pal_panel)

        self.prop_panel = PropsPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.prop_panel)

        self.cam_panel = CamPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.cam_panel)

        self.thread_panel = ThreadPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.thread_panel)

        # Tabify Docks to prevent vertical height overflow
        self.tabifyDockWidget(self.pal_panel, self.prop_panel)
        self.tabifyDockWidget(self.prop_panel, self.thread_panel)
        self.tabifyDockWidget(self.thread_panel, self.cam_panel)
        self.cam_panel.raise_()  # Default to CAM panel

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._setup_toolbars()
        self.sync_all()

        # Autosave (3 dakika)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start(180000)
        self._check_recovery()

    def _setup_toolbars(self):
        # ── Sol: Çizim Araçları ──
        tb = QToolBar("Araçlar")
        self.addToolBar(Qt.LeftToolBarArea, tb)
        for t in ('pencil', 'eraser', 'fill', 'line', 'rect', 'select'):
            act = QAction(t.capitalize(), self)
            act.triggered.connect(
                lambda checked, t_id=t: self.set_tool(t_id))
            tb.addAction(act)

        tb.addSeparator()
        act_cp = QAction("Kopyala", self)
        act_cp.setShortcut("Ctrl+C")
        act_cp.triggered.connect(self.canvas.exec_copy)
        act_ps = QAction("Yapıştır", self)
        act_ps.setShortcut("Ctrl+V")
        act_ps.triggered.connect(self.canvas.exec_paste)
        tb.addActions([act_cp, act_ps])

        # ── Üst: Dosya & Görünüm ──
        mtb = QToolBar("Menü")
        self.addToolBar(Qt.TopToolBarArea, mtb)

        act_new = QAction("Yeni", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self.cmd_new)
        act_open = QAction("Aç", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.cmd_open)
        act_save = QAction("Kaydet", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.cmd_save)
        mtb.addActions([act_new, act_open, act_save])
        mtb.addSeparator()

        act_imp = QAction("Resim Import", self)
        act_imp.triggered.connect(self.cmd_import)
        act_imp_jc5 = QAction("JC5 İçe Aktar", self)
        act_imp_jc5.triggered.connect(self.cmd_import_jc5)
        act_exp = QAction("Çıktı Export (PNG)", self)
        act_exp.triggered.connect(self.cmd_export)
        mtb.addActions([act_imp, act_imp_jc5, act_exp])
        mtb.addSeparator()

        act_undo = self.history.createUndoAction(self, "Geri Al")
        act_undo.setShortcut("Ctrl+Z")
        act_redo = self.history.createRedoAction(self, "İleri Al")
        act_redo.setShortcut("Ctrl+Y")
        mtb.addActions([act_undo, act_redo])
        mtb.addSeparator()

        act_tech = QAction("Teknik B/W", self)
        act_tech.setCheckable(True)
        act_tech.triggered.connect(self._toggle_tech)
        mtb.addAction(act_tech)

        act_toggle = QAction("Görünüm Döngüsü (D/W/F)", self)
        act_toggle.setShortcut("F5")
        act_toggle.triggered.connect(self._toggle_view)
        mtb.addAction(act_toggle)

    # ── Commands ────────────────────────────────────────────

    def sync_all(self):
        self.canvas.rebuild_qimage()
        self.pal_panel.refresh()
        self.prop_panel.refresh()
        self.cam_panel.refresh()

    def set_tool(self, t):
        self.active_tool = t
        self.status.showMessage(f"Araç: {t.capitalize()}")

    def _toggle_tech(self, state):
        self.doc.is_technical = state
        self.canvas.update_palette()

    def _toggle_view(self):
        """3-yönlü: design → weave → fabric → design."""
        v = getattr(self.doc, 'view_mode', 'design')
        if v == 'design':
            if getattr(self.doc, 'lift_plan', None) is None:
                self.status.showMessage(
                    "CAM panelinden Lift Plan derlemelisiniz.")
                return
            self.doc.view_mode = 'weave'
        elif v == 'weave':
            if getattr(self.doc, 'fabric_rgb', None) is not None:
                self.doc.view_mode = 'fabric'
            else:
                self.doc.view_mode = 'design'
        else:
            self.doc.view_mode = 'design'
        self.canvas.rebuild_qimage()
        self.status.showMessage(
            f"Görünüm: {self.doc.view_mode.upper()}")

    def cmd_new(self):
        if self.doc.is_dirty:
            r = QMessageBox.question(
                self, "Kaydet?",
                "Değişiklikler kaydedilmedi. Kaydetmek ister misiniz?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if r == QMessageBox.Yes:
                self.cmd_save()
            elif r == QMessageBox.Cancel:
                return
        self.doc = Document(200, 200)
        self.history.clear()
        self.sync_all()

    def cmd_open(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Aç", "", "Jakar (*.tcad)")
        if p:
            load_project(self.doc, p)
            self.history.clear()
            self.sync_all()
            self.setWindowTitle(
                f"Jacquard CAD Professional — {os.path.basename(p)}")

    def cmd_save(self):
        if not self.doc.file_path:
            p, _ = QFileDialog.getSaveFileName(
                self, "Kaydet", "", "Jakar (*.tcad)")
            if not p:
                return
            self.doc.file_path = p
        save_project(self.doc, self.doc.file_path)
        self.status.showMessage("Kaydedildi.")
        self.setWindowTitle(
            f"Jacquard CAD Professional — "
            f"{os.path.basename(self.doc.file_path)}")

    def cmd_import(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "İçe Aktar", "",
            "Resim (*.png *.bmp *.tif *.tiff *.jpg *.jpeg)")
        if p:
            import_image(self.doc, p)
            self.history.clear()
            self.sync_all()

    def cmd_import_jc5(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "JC5 İçe Aktar", "", "Staubli JC5 (*.jc5)")
        if p:
            import_jc5(self.doc, p)
            self.history.clear()
            self.sync_all()

    def cmd_export(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Dışa Aktar", "", "PNG (*.png)")
        if p:
            export_png(self.doc, p)
            self.status.showMessage("Dışa Aktarıldı.")

    def _autosave(self):
        if self.doc.is_dirty:
            p = os.path.join(tempfile.gettempdir(), "tcad_recovery.tcad")
            try:
                save_project(self.doc, p)
            except Exception:
                pass

    def _check_recovery(self):
        p = os.path.join(tempfile.gettempdir(), "tcad_recovery.tcad")
        if os.path.exists(p):
            r = QMessageBox.question(
                self, "Kurtarma",
                "Önceki oturumdan kurtarma bulundu. Yüklensin mi?")
            if r == QMessageBox.Yes:
                load_project(self.doc, p)
                self.sync_all()
            else:
                os.remove(p)

    def closeEvent(self, event):
        if self.doc.is_dirty:
            r = QMessageBox.question(
                self, "Çıkış",
                "Değişiklikler kaydedilmedi. Kaydetmek ister misiniz?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if r == QMessageBox.Yes:
                self.cmd_save()
                event.accept()
            elif r == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
