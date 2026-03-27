"""Özel Tahar & Kanca (Mapping) Editörü — Ölü kanca, çakışma analizi."""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget,
                                QTableWidgetItem, QPushButton, QHBoxLayout,
                                QLabel, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
import numpy as np


class CustomMappingDialog(QDialog):
    """Her çözgü teli için makine kanca indeksi atama ve çakışma testi."""

    def __init__(self, doc, total_hooks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Özel Tahar & Kanca (Mapping) Editörü")
        self.resize(500, 600)
        self.doc = doc
        self.total_hooks = total_hooks
        self.result_mapping = None

        cm = doc.custom_mapping
        if cm is not None and len(cm) == doc.width:
            self.working_mapping = cm.copy()
        else:
            self.working_mapping = np.arange(doc.width) % total_hooks

        l = QVBoxLayout(self)
        l.addWidget(QLabel(
            "Her çözgü teli için makine kanca (hook) indeksini girin.\n"
            "İptal etmek/koparmak istediğiniz kancalar için -1 girin."))

        self.table = QTableWidget(doc.width, 2)
        self.table.setHorizontalHeaderLabels(
            ["Çözgü Teli (Warp)", "Makine Kancası (Hook)"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)

        for i in range(doc.width):
            item_w = QTableWidgetItem(f"Tel {i}")
            item_w.setFlags(item_w.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item_w)
            val = str(self.working_mapping[i])
            self.table.setItem(i, 1, QTableWidgetItem(val))
        l.addWidget(self.table)

        hbox = QHBoxLayout()
        btn_check = QPushButton("Çarpışma (Collision) Testi")
        btn_check.clicked.connect(self.check_collision)
        btn_apply = QPushButton("Haritayı Kaydet")
        btn_apply.setStyleSheet("background-color: #27ae60; color: white;")
        btn_apply.clicked.connect(self.save_mapping)

        hbox.addWidget(btn_check)
        hbox.addWidget(btn_apply)
        l.addLayout(hbox)

    def parse_table(self):
        new_map = np.zeros(self.doc.width, dtype=np.int32)
        for i in range(self.doc.width):
            try:
                val = int(self.table.item(i, 1).text())
                new_map[i] = val if val < self.total_hooks else -1
            except (ValueError, AttributeError):
                new_map[i] = -1
        return new_map

    def check_collision(self):
        arr = self.parse_table()
        valid = arr[arr >= 0]
        unique, counts = np.unique(valid, return_counts=True)
        collisions = unique[counts > 1]

        if len(collisions) > 0:
            msg = (f"{len(collisions)} adet kancaya birden fazla tel atanmış! "
                   f"(Örn: {collisions[:5]})\n"
                   f"Donanım 'Bitwise OR' uygulayarak bu iplikleri "
                   f"birlikte kaldıracaktır.")
            QMessageBox.information(self, "Tahar Analizi", msg)
        else:
            QMessageBox.information(
                self, "Tahar Analizi",
                "Tüm teller benzersiz kancalara atanmış. Çarpışma yok.")

    def save_mapping(self):
        self.result_mapping = self.parse_table()
        self.accept()
