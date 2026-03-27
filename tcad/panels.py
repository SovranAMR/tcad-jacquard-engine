"""Arayüz Dock panelleri — Endüstriyel Palet ve Doküman/Rapor."""

from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QListWidget,
                                QListWidgetItem, QSpinBox, QLabel,
                                QColorDialog, QFormLayout)
from PySide6.QtGui import QPixmap, QColor, QIcon
from PySide6.QtCore import Qt, QSize


class PalettePanel(QDockWidget):
    """İndeksli renk paleti yönetim paneli."""

    def __init__(self, mw):
        super().__init__("Endüstriyel Palet", mw)
        self.mw = mw
        w = QWidget()
        l = QVBoxLayout(w)

        self.list = QListWidget()
        self.list.setIconSize(QSize(24, 24))
        self.list.currentRowChanged.connect(self.selection_changed)
        self.list.itemDoubleClicked.connect(self.edit_color)

        l.addWidget(QLabel("Çift Tıkla: Rengi Düzenle"))
        l.addWidget(self.list)
        self.setWidget(w)

    def refresh(self):
        self.list.blockSignals(True)
        self.list.clear()
        for i, (r, g, b) in enumerate(self.mw.doc.palette):
            item = QListWidgetItem(f"İndeks {i}")
            pm = QPixmap(24, 24)
            pm.fill(QColor(r, g, b))
            item.setIcon(QIcon(pm))
            self.list.addItem(item)
        self.list.setCurrentRow(1)
        self.list.blockSignals(False)

    def selection_changed(self, row):
        if row >= 0:
            self.mw.active_color = row

    def edit_color(self, item):
        idx = self.list.row(item)
        c = QColorDialog.getColor(
            QColor(*self.mw.doc.palette[idx]), self, "Varyant Rengi Seç")
        if c.isValid():
            self.mw.doc.palette[idx] = (c.red(), c.green(), c.blue())
            self.refresh()
            self.mw.canvas.update_palette()


class PropsPanel(QDockWidget):
    """Doküman ölçüleri ve rapor (repeat) ayarları paneli."""

    def __init__(self, mw):
        super().__init__("Doküman / Rapor", mw)
        self.mw = mw
        w = QWidget()
        l = QFormLayout(w)

        self.lbl_size = QLabel()
        self.sp_rx = QSpinBox()
        self.sp_rx.setRange(1, 100)
        self.sp_rx.valueChanged.connect(self.update_rep)
        self.sp_ry = QSpinBox()
        self.sp_ry.setRange(1, 100)
        self.sp_ry.valueChanged.connect(self.update_rep)

        l.addRow("Ölçü:", self.lbl_size)
        l.addRow("Yatay Tekrar:", self.sp_rx)
        l.addRow("Dikey Tekrar:", self.sp_ry)
        self.setWidget(w)

    def refresh(self):
        d = self.mw.doc
        self.lbl_size.setText(f"{d.width} tel x {d.height} atkı")
        self.sp_rx.blockSignals(True)
        self.sp_rx.setValue(d.repeat_x)
        self.sp_rx.blockSignals(False)
        self.sp_ry.blockSignals(True)
        self.sp_ry.setValue(d.repeat_y)
        self.sp_ry.blockSignals(False)

    def update_rep(self):
        self.mw.doc.repeat_x = self.sp_rx.value()
        self.mw.doc.repeat_y = self.sp_ry.value()
        self.mw.canvas.gfx_scene.setSceneRect(
            self.mw.canvas.item.boundingRect())
        self.mw.canvas.gfx_scene.update()
