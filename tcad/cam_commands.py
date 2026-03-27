"""CAM işlemleri için Undo/Redo komutları — History entegrasyonu."""

from PySide6.QtGui import QUndoCommand
import numpy as np


class AssignWeaveCommand(QUndoCommand):
    """Örgü atama işlemini geri alınabilir yapar."""

    def __init__(self, doc, is_region, target_id, old_weave, new_weave, update_cb):
        target_name = f"Bölge {target_id}" if is_region else f"İndeks {target_id}"
        super().__init__(f"Örgü Ata ({target_name})")
        self.doc = doc
        self.is_region = is_region
        self.target_id = target_id
        self.old_w = old_weave.copy() if old_weave is not None else None
        self.new_w = new_weave.copy() if new_weave is not None else None
        self.update_cb = update_cb

    def undo(self):
        target_dict = self.doc.region_weaves if self.is_region else self.doc.color_weaves
        target_dict[self.target_id] = self.old_w
        self.doc.is_dirty = True
        self.update_cb()

    def redo(self):
        target_dict = self.doc.region_weaves if self.is_region else self.doc.color_weaves
        target_dict[self.target_id] = self.new_w
        self.doc.is_dirty = True
        self.update_cb()


class ApplyRegionMaskCommand(QUndoCommand):
    """Bölge maskesi çizimini geri alınabilir yapar."""

    def __init__(self, doc, x, y, w, h, region_id, update_cb):
        super().__init__(f"Bölge Maskesi Çiz (ID {region_id})")
        self.doc = doc
        self.x, self.y, self.w, self.h = x, y, w, h
        self.region_id = region_id
        self.old_mask = doc.region_mask[y:y + h, x:x + w].copy()
        self.new_mask = np.full((h, w), region_id, dtype=np.uint8)
        self.update_cb = update_cb
        self._first = True

    def undo(self):
        self.doc.region_mask[self.y:self.y + self.h,
                             self.x:self.x + self.w] = self.old_mask
        self.doc.is_dirty = True
        self.update_cb()

    def redo(self):
        if self._first:
            self._first = False
            return
        self.doc.region_mask[self.y:self.y + self.h,
                             self.x:self.x + self.w] = self.new_mask
        self.doc.is_dirty = True
        self.update_cb()


class UpdateMappingCommand(QUndoCommand):
    """Tahar haritası güncellemesini geri alınabilir yapar."""

    def __init__(self, doc, old_map, new_map, update_cb):
        super().__init__("Tahar Haritası Güncelle")
        self.doc = doc
        self.old_map = old_map.copy() if old_map is not None else None
        self.new_map = new_map.copy()
        self.update_cb = update_cb

    def undo(self):
        self.doc.custom_mapping = self.old_map
        self.doc.is_dirty = True
        self.update_cb()

    def redo(self):
        self.doc.custom_mapping = self.new_map
        self.doc.is_dirty = True
        self.update_cb()

class AutoFixFloatsCommand(QUndoCommand):
    """Otomatik atlama düzeltme işlemini geri alınabilir yapar."""

    def __init__(self, doc, old_plan, new_plan, fix_count, update_cb):
        super().__init__(f"Otomatik Düzelt ({fix_count} bağ eklendi)")
        self.doc = doc
        self.old_plan = old_plan.copy()
        self.new_plan = new_plan.copy()
        self.update_cb = update_cb

    def undo(self):
        self.doc.lift_plan = self.old_plan
        self.doc.is_dirty = True
        self.update_cb()

    def redo(self):
        self.doc.lift_plan = self.new_plan
        self.doc.is_dirty = True
        self.update_cb()
