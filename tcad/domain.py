"""Veri mimarisinin kalbi — Document (Tek Gerçeklik Kaynağı) ve PatchCommand (Delta History)."""

import numpy as np
from PySide6.QtGui import QUndoCommand


from dataclasses import dataclass

@dataclass
class Yarn:
    """İplik stok ve maliyet hesabı için fiziksel veri modeli."""
    color: tuple[int, int, int]
    name: str = "Standart İplik"
    tex: int = 30
    price_kg: float = 0.0

class Document:
    """Tek Gerçeklik Kaynağı. Tüm proje verisi burada yaşar."""

    def __init__(self, w=400, h=400):
        self.width = w
        self.height = h
        # C-contiguous matris — QImage'ın belleği doğrudan okuyabilmesi için zorunlu
        self.grid = np.zeros((h, w), dtype=np.uint8)

        self.palette = [
            (255, 255, 255), (0, 0, 0), (255, 0, 0),
            (0, 255, 0), (0, 0, 255),
        ]
        while len(self.palette) < 256:
            self.palette.append((128, 128, 128))
            
        self.yarns = {i: Yarn(color=c, name=f"İplik {i}") for i, c in enumerate(self.palette)}

        self.repeat_x = 1
        self.repeat_y = 1
        self.epc = 40  # Ends per cm (Çözgü Sıklığı)
        self.ppc = 40  # Picks per cm (Atkı Sıklığı)
        self.is_technical = False
        self.file_path = None
        self.is_dirty = False

        # --- ÜRETİM (CAM) KATMANI ---
        from tcad.weaves import WeaveLibrary
        from tcad.threads import ThreadSequence

        self.color_weaves = {i: None for i in range(256)}
        self.color_weaves[1] = WeaveLibrary.plain()

        self.region_weaves = {}  # region_id (int) -> Weave Matrix
        self.region_mask = np.zeros((h, w), dtype=np.uint8)

        self.hook_count = 2688
        self.custom_mapping = None  # Hook mapping dizisi (np array veya None)

        self.lift_plan = None
        self.view_mode = 'design'  # 'design' | 'weave' | 'fabric'
        self.float_errors = []

        # İplik Planlama
        self.warp_seq = ThreadSequence((240, 240, 240))
        self.weft_seq = ThreadSequence((30, 30, 30))
        self.weave_phases = {}  # "c_1": (px, py) veya "r_2": (px, py)
        self.fabric_rgb = None

    def resize(self, w, h):
        new_grid = np.zeros((h, w), dtype=np.uint8)
        min_w, min_h = min(w, self.width), min(h, self.height)
        new_grid[:min_h, :min_w] = self.grid[:min_h, :min_w]
        self.grid = new_grid

        old_mask = getattr(self, 'region_mask',
                           np.zeros((self.height, self.width), dtype=np.uint8))
        new_mask = np.zeros((h, w), dtype=np.uint8)
        new_mask[:min_h, :min_w] = old_mask[:min_h, :min_w]
        self.region_mask = new_mask

        self.width = w
        self.height = h
        self.is_dirty = True


class PatchCommand(QUndoCommand):
    """Bellek şişmesini engelleyen O(1) Sparse (Seyrek) Delta History yapısı."""

    def __init__(self, doc, x, y, old_patch, new_patch, update_cb, text="Draw"):
        super().__init__(text)
        self.doc = doc
        self.update_cb = update_cb
        
        # Sadece Bounding Box içindeki O GERÇEKTEN DEĞİŞEN pikselleri bul
        mask = old_patch != new_patch
        cy, cx = np.nonzero(mask)
        
        self.cy = cy + y
        self.cx = cx + x
        self.old_vals = old_patch[mask].copy()
        self.new_vals = new_patch[mask].copy()
        
        # Redraw bounding box hesaplamak için
        if len(self.cy) > 0:
            self.bx = int(np.min(self.cx))
            self.by = int(np.min(self.cy))
            self.bw = int(np.max(self.cx) - self.bx) + 1
            self.bh = int(np.max(self.cy) - self.by) + 1
        else:
            self.bx, self.by, self.bw, self.bh = x, y, 1, 1

        self._applied = True

    def undo(self):
        self.doc.grid[self.cy, self.cx] = self.old_vals
        self.doc.is_dirty = True
        self._applied = False
        self.update_cb(self.bx, self.by, self.bw, self.bh)

    def redo(self):
        if self._applied:
            return
        self.doc.grid[self.cy, self.cx] = self.new_vals
        self.doc.is_dirty = True
        self._applied = True
        self.update_cb(self.bx, self.by, self.bw, self.bh)
