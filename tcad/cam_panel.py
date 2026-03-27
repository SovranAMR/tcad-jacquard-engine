"""CAM / Jakar Üretim Hattı Paneli — Region-based weave, validation, adapter export."""

import os
from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QComboBox,
                                QPushButton, QTableWidget, QTableWidgetItem,
                                QFormLayout, QLabel, QMessageBox, QFileDialog,
                                QSpinBox, QHBoxLayout)
import numpy as np

from tcad.weaves import WeaveLibrary, WeaveEngine
from tcad.validation import ValidationEngine
from tcad.adapters import AdapterRegistry
from tcad.tech_sheet import TechnicalSheet
from tcad.mapping_editor import CustomMappingDialog
from tcad.cam_commands import (AssignWeaveCommand, ApplyRegionMaskCommand,
                                UpdateMappingCommand, AutoFixFloatsCommand)


class CamPanel(QDockWidget):
    """Üretim kontrol arayüzü — örgü atama, derleme, doğrulama, export."""

    def __init__(self, mw):
        super().__init__("CAM / Jakar Pipeline", mw)
        self.mw = mw
        w = QWidget()
        l = QVBoxLayout(w)

        # 1. Örgü Atama
        form = QFormLayout()
        self.cmb_weaves = QComboBox()
        self.cmb_weaves.addItems(
            ["(Yok)", "Bezayağı", "Dimi 2/1", "Saten 5'li"])
        form.addRow("Örgü:", self.cmb_weaves)

        self.btn_color = QPushButton("Aktif Renge Ata (Global)")
        self.btn_color.clicked.connect(lambda: self.assign_weave(False))

        self.sp_region = QSpinBox()
        self.sp_region.setRange(1, 10)
        self.sp_region.setPrefix("Bölge ID: ")
        self.btn_draw_region = QPushButton("Seçimi Maske Yap")
        self.btn_draw_region.clicked.connect(self.draw_region_mask)
        self.btn_region = QPushButton("Aktif Bölgeye Ata (Override)")
        self.btn_region.setStyleSheet(
            "background-color: #8e44ad; color: white;")
        self.btn_region.clicked.connect(lambda: self.assign_weave(True))

        l.addLayout(form)
        l.addWidget(self.btn_color)
        h_reg = QHBoxLayout()
        h_reg.addWidget(self.sp_region)
        h_reg.addWidget(self.btn_draw_region)
        l.addLayout(h_reg)
        l.addWidget(self.btn_region)
        l.addSpacing(10)

        # 2. Makine ve Tahar
        self.sp_hooks = QSpinBox()
        self.sp_hooks.setRange(100, 20000)
        self.btn_map_edit = QPushButton("Özel Tahar Editörü...")
        self.btn_map_edit.clicked.connect(self.open_mapping_editor)

        form2 = QFormLayout()
        form2.addRow("Kanca Sayısı:", self.sp_hooks)
        form2.addRow("Tahar Planı:", self.btn_map_edit)
        l.addLayout(form2)
        l.addSpacing(10)

        # 3. Fiziksel Kumaş Parametreleri
        self.sp_warp_cm = QSpinBox()
        self.sp_warp_cm.setRange(1, 300)
        self.sp_warp_cm.setValue(40)
        self.sp_weft_cm = QSpinBox()
        self.sp_weft_cm.setRange(1, 300)
        self.sp_weft_cm.setValue(35)
        self.sp_warp_tex = QSpinBox()
        self.sp_warp_tex.setRange(1, 1000)
        self.sp_warp_tex.setValue(30)
        self.sp_weft_tex = QSpinBox()
        self.sp_weft_tex.setRange(1, 1000)
        self.sp_weft_tex.setValue(30)

        form3 = QFormLayout()
        form3.addRow("Çözgü (tel/cm):", self.sp_warp_cm)
        form3.addRow("Atkı (tel/cm):", self.sp_weft_cm)
        form3.addRow("Çözgü İplik (Tex):", self.sp_warp_tex)
        form3.addRow("Atkı İplik (Tex):", self.sp_weft_tex)
        l.addLayout(form3)
        l.addSpacing(10)

        # 4. Derleme & Doğrulama & Export
        self.btn_compile = QPushButton("1. Katmanlı Lift Plan Derle")
        self.btn_compile.setStyleSheet(
            "background-color: #2c3e50; color: white;")
        self.btn_compile.clicked.connect(self.compile_plan)

        self.btn_val = QPushButton(
            "2. Risk Analizi (Rapor Wrap & İzole Bağ)")
        self.btn_val.clicked.connect(self.validate_plan)

        self.table_err = QTableWidget(0, 4)
        self.table_err.setHorizontalHeaderLabels(["Tür", "X", "Y", "Hata / Uzunluk"])
        self.table_err.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_err.itemSelectionChanged.connect(self.on_error_select)

        self.btn_auto_fix = QPushButton("🛠 Otomatik Atlamaları Çöz")
        self.btn_auto_fix.setStyleSheet(
            "background-color: #d35400; color: white;")
        self.btn_auto_fix.clicked.connect(self.auto_fix_plan)

        # 4. Export & Rapor
        self.cmb_adapters = QComboBox()
        for a in AdapterRegistry.get_all():
            self.cmb_adapters.addItem(a.name, a)

        l.addWidget(self.btn_compile)
        l.addWidget(self.btn_val)
        l.addWidget(self.table_err)
        l.addWidget(self.btn_auto_fix)
        l.addWidget(QLabel("Format Adapter:"))
        l.addWidget(self.cmb_adapters)

        self.btn_report = QPushButton("📄 Teknik Üretim Raporu Al")
        self.btn_report.clicked.connect(self.generate_report)

        self.btn_export = QPushButton("🚀 Makine Formatına Çevir")
        self.btn_export.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 10px;")
        self.btn_export.clicked.connect(self.export_loom)

        l.addWidget(self.btn_report)
        l.addWidget(self.btn_export)
        self.setWidget(w)

    def refresh(self):
        doc = self.mw.doc
        self.sp_hooks.blockSignals(True)
        self.sp_hooks.setValue(doc.hook_count)
        self.sp_hooks.blockSignals(False)

    def _get_selected_weave(self):
        sel = self.cmb_weaves.currentIndex()
        if sel == 1:
            return WeaveLibrary.plain()
        elif sel == 2:
            return WeaveLibrary.twill(2, 1)
        elif sel == 3:
            return WeaveLibrary.satin(5, 2)
        return None

    def assign_weave(self, is_region):
        doc = self.mw.doc
        w = self._get_selected_weave()
        target_id = (self.sp_region.value()
                     if is_region else self.mw.active_color)
        old_w = (doc.region_weaves.get(target_id)
                 if is_region else doc.color_weaves.get(target_id))

        cmd = AssignWeaveCommand(
            doc, is_region, target_id, old_w, w,
            lambda: self.mw.status.showMessage("Örgü Atandı."))
        self.mw.history.push(cmd)

    def draw_region_mask(self):
        if not self.mw.canvas.selection_rect:
            return QMessageBox.warning(
                self, "Uyarı",
                "Kanvastan (Select aracı ile) bir alan seçin.")
        r = self.mw.canvas.selection_rect
        x, y = int(r.x()), int(r.y())
        w, h = int(r.width()), int(r.height())
        if w <= 0 or h <= 0:
            return
        cmd = ApplyRegionMaskCommand(
            self.mw.doc, x, y, w, h,
            self.sp_region.value(),
            lambda: self.mw.canvas.gfx_scene.update())
        self.mw.history.push(cmd)
        self.mw.canvas.selection_rect = None

    def open_mapping_editor(self):
        doc = self.mw.doc
        dlg = CustomMappingDialog(doc, self.sp_hooks.value(), self)
        if dlg.exec():
            cmd = UpdateMappingCommand(
                doc, doc.custom_mapping, dlg.result_mapping,
                lambda: self.mw.status.showMessage("Tahar güncellendi."))
            self.mw.history.push(cmd)

    def compile_plan(self):
        doc = self.mw.doc
        doc.hook_count = self.sp_hooks.value()
        doc.lift_plan = WeaveEngine.build_lift_plan(
            doc.grid, doc.region_mask,
            doc.color_weaves, doc.region_weaves,
            doc.weave_phases)
        doc.view_mode = 'weave'
        self.mw.canvas.rebuild_qimage()
        self.mw.status.showMessage("Lift Plan derlendi. Örgü görünümünde.")

    def validate_plan(self):
        doc = self.mw.doc
        if getattr(doc, 'lift_plan', None) is None:
            return QMessageBox.warning(self, "Hata", "Önce Derleyin.")
        errors = ValidationEngine.analyze_fabric(
            doc.lift_plan, 7, 7, region_mask=doc.region_mask)
        doc.float_errors = errors
        self.table_err.setRowCount(len(errors))
        for i, err in enumerate(errors):
            self.table_err.setItem(
                i, 0, QTableWidgetItem(err['type']))
            self.table_err.setItem(
                i, 1, QTableWidgetItem(str(err['len'])))
            self.table_err.setItem(
                i, 2, QTableWidgetItem(str(err['x'])))
            self.table_err.setItem(
                i, 3, QTableWidgetItem(str(err['y'])))
        self.mw.canvas.gfx_scene.update()

    def on_error_select(self):
        sel = self.table_err.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        err = self.mw.doc.float_errors[row]
        x, y = err['x'], err['y']
        # Pan to error
        self.mw.canvas.centerOn(x, y)
        self.mw.status.showMessage(f"Hata: {err['type']} ({x}, {y}) L:{err['len']}")

    def auto_fix_plan(self):
        doc = self.mw.doc
        if getattr(doc, 'lift_plan', None) is None:
            return QMessageBox.warning(self, "Hata", "Önce Derleyin.")
            
        fixed_plan, total_fixes = ValidationEngine.auto_fix_floats(
            doc.lift_plan, 7, 7, doc.region_mask)
            
        if total_fixes == 0:
            return QMessageBox.information(self, "Bilgi", "Düzeltilecek atlama bulunamadı!")
            
        cmd = AutoFixFloatsCommand(
            doc, doc.lift_plan, fixed_plan, total_fixes,
            lambda: self._on_auto_fix_done(total_fixes))
        self.mw.history.push(cmd)

    def _on_auto_fix_done(self, count):
        self.validate_plan()
        self.mw.canvas.rebuild_qimage()
        self.mw.status.showMessage(f"Otomatik Düzeltme: {count} atlama çözüldü.")

    def generate_report(self):
        doc = self.mw.doc
        adapter = self.cmb_adapters.currentData()
        
        p, _ = QFileDialog.getSaveFileName(
            self, "Üretim Raporu Kaydet", "",
            "Metin Belgesi (*.txt)")
        if not p:
            return

        try:
            phys_params = {
                'ends_per_cm': self.sp_warp_cm.value(),
                'picks_per_cm': self.sp_weft_cm.value(),
                'tex_warp': self.sp_warp_tex.value(),
                'tex_weft': self.sp_weft_tex.value()
            }
            sheet_dict = TechnicalSheet.generate(
                doc, adapter.profile, phys_params=phys_params)
            TechnicalSheet.export_text(sheet_dict, p)
            self.mw.status.showMessage("Rapor kaydedildi.")
            QMessageBox.information(
                self, "Rapor Alındı",
                "Üretim raporu başarıyla dışa aktarıldı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor hatası: {e}")

    def export_loom(self):
        doc = self.mw.doc
        if getattr(doc, 'lift_plan', None) is None:
            return QMessageBox.warning(self, "Hata", "Önce Derleyin.")
        
        adapter = self.cmb_adapters.currentData()

        # Constraints / Acceptance Gate
        can_export, errors = adapter.can_export(doc)
        if not can_export:
            err_text = "\n".join(f"- {e['message']} (Tip: {e['code']})" for e in errors)
            return QMessageBox.critical(
                self, "Üretim Kısıtları İhlali (Reddedildi)", 
                f"Makine profiline ({adapter.profile.name}) uyumsuz desen!\n\n{err_text}")

        p, _ = QFileDialog.getSaveFileName(
            self, "Makine Çıktısı", "",
            f"Makine Dosyası (*{adapter.extension})")
        if p:
            try:
                picks, ends = doc.lift_plan.shape
                cm = (doc.custom_mapping
                      if doc.custom_mapping is not None
                      else np.arange(ends) % doc.hook_count)
                m_plan = np.zeros(
                    (picks, doc.hook_count), dtype=np.uint8)

                valid = cm >= 0
                if np.any(valid):
                    row_idx = np.arange(picks)[:, None]
                    col_idx = cm[valid][None, :]
                    np.bitwise_or.at(
                        m_plan, (row_idx, col_idx),
                        doc.lift_plan[:, valid])

                result_metadata = adapter.export(doc, m_plan, p)
                
                info = (f"Export Başarılı!\n"
                        f"Makine: {result_metadata['adapter']}\n"
                        f"Picks: {result_metadata['picks']}, Hooks: {result_metadata['hooks']}\n"
                        f"Not: {result_metadata['note']}")
                
                QMessageBox.information(self, "Tamamlandı", info)
                self.mw.status.showMessage(f"Export tamamlandı ({len(result_metadata['files'])} dosya)")
            except Exception as e:
                QMessageBox.critical(
                    self, "Donanım Reddi", str(e))
