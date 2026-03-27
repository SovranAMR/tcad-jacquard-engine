"""İplik Reçetesi & Örgü Fazı (Phase) UI paneli."""

from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QColorDialog,
                                QHBoxLayout, QLabel, QSpinBox)
from PySide6.QtGui import QColor


class ThreadPanel(QDockWidget):
    """Çözgü/atkı dizilimi, faz kaydırma ve kumaş simülasyonu kontrolü."""

    def __init__(self, mw):
        super().__init__("İplik Reçetesi & Örgü Fazı", mw)
        self.mw = mw
        w = QWidget()
        l = QVBoxLayout(w)

        l.addWidget(QLabel("Çözgü (Warp) Raporu:"))
        self.tb_warp = QTableWidget(0, 2)
        self.tb_warp.setHorizontalHeaderLabels(["Renk", "Tel"])
        btn_warp = QPushButton("+ Çözgü Ekle")
        btn_warp.clicked.connect(lambda: self.add_yarn('warp'))
        l.addWidget(self.tb_warp)
        l.addWidget(btn_warp)

        l.addWidget(QLabel("Atkı (Weft) Raporu:"))
        self.tb_weft = QTableWidget(0, 2)
        self.tb_weft.setHorizontalHeaderLabels(["Renk", "Atım"])
        btn_weft = QPushButton("+ Atkı Ekle")
        btn_weft.clicked.connect(lambda: self.add_yarn('weft'))
        l.addWidget(self.tb_weft)
        l.addWidget(btn_weft)

        l.addSpacing(10)
        l.addWidget(QLabel("Aktif Renk için Örgü Fazı:"))
        h_phase = QHBoxLayout()
        self.sp_px = QSpinBox()
        self.sp_px.setRange(-100, 100)
        self.sp_px.setPrefix("X: ")
        self.sp_py = QSpinBox()
        self.sp_py.setRange(-100, 100)
        self.sp_py.setPrefix("Y: ")
        btn_phase = QPushButton("Kaydır")
        btn_phase.clicked.connect(self.apply_phase)
        h_phase.addWidget(self.sp_px)
        h_phase.addWidget(self.sp_py)
        h_phase.addWidget(btn_phase)
        l.addLayout(h_phase)

        self.btn_sim = QPushButton("İplikleri Uygula & Kumaşı Gör")
        self.btn_sim.setStyleSheet(
            "background-color: #d35400; color: white;")
        self.btn_sim.clicked.connect(self.apply_threads)
        l.addSpacing(10)
        l.addWidget(self.btn_sim)

        self.setWidget(w)
        self._colors = {'warp': [], 'weft': []}

    def add_yarn(self, target):
        c = QColorDialog.getColor()
        if c.isValid():
            tb = self.tb_warp if target == 'warp' else self.tb_weft
            row = tb.rowCount()
            tb.insertRow(row)
            item = QTableWidgetItem(
                f"RGB({c.red()},{c.green()},{c.blue()})")
            item.setBackground(c)
            tb.setItem(row, 0, item)
            tb.setItem(row, 1, QTableWidgetItem("10"))
            self._colors[target].append(
                (c.red(), c.green(), c.blue()))

    def apply_phase(self):
        idx = self.mw.active_color
        self.mw.doc.weave_phases[f"c_{idx}"] = (
            self.sp_px.value(), self.sp_py.value())
        self.mw.status.showMessage(
            f"Renk {idx} Faz X:{self.sp_px.value()}, "
            f"Y:{self.sp_py.value()}")
        if getattr(self.mw.doc, 'lift_plan', None) is not None:
            self.mw.cam_panel.compile_plan()

    def apply_threads(self):
        doc = self.mw.doc

        if self._colors['warp']:
            doc.warp_seq.sequence.clear()
            for i in range(self.tb_warp.rowCount()):
                cnt_item = self.tb_warp.item(i, 1)
                cnt = int(cnt_item.text()) if cnt_item else 1
                doc.warp_seq.sequence.append(
                    (self._colors['warp'][i], cnt))

        if self._colors['weft']:
            doc.weft_seq.sequence.clear()
            for i in range(self.tb_weft.rowCount()):
                cnt_item = self.tb_weft.item(i, 1)
                cnt = int(cnt_item.text()) if cnt_item else 1
                doc.weft_seq.sequence.append(
                    (self._colors['weft'][i], cnt))

        if getattr(doc, 'lift_plan', None) is not None:
            from tcad.threads import FabricSimulator
            doc.fabric_rgb = FabricSimulator.render_fabric(
                doc.lift_plan, doc.warp_seq, doc.weft_seq)
            doc.view_mode = 'fabric'
            self.mw.canvas.rebuild_qimage()
            self.mw.status.showMessage(
                "32-bit Kumaş Simülasyonu Aktif.")
        else:
            self.mw.status.showMessage(
                "İplikler kaydedildi. Önce CAM'den Derleyin.")
