"""Örgü matrisleri ve Phase-Aligned Lift Plan motoru (V4 — Region + Phase)."""

import numpy as np


class WeaveLibrary:
    """Sanayi standardı dokuma örgüleri (1: Çözgü Üstte, 0: Atkı Üstte)."""

    @staticmethod
    def plain():
        return np.array([[1, 0], [0, 1]], dtype=np.uint8)

    @staticmethod
    def twill(up=2, down=1, step=1):
        size = up + down
        base = np.zeros(size, dtype=np.uint8)
        base[:up] = 1
        weave = np.zeros((size, size), dtype=np.uint8)
        for i in range(size):
            weave[i] = np.roll(base, i * step)
        return weave

    @staticmethod
    def satin(size=5, step=2):
        weave = np.zeros((size, size), dtype=np.uint8)
        for i in range(size):
            weave[i, (i * step) % size] = 1
        return weave


class WeaveEngine:
    """Phase-aligned lift plan builder with region override support."""

    @staticmethod
    def build_lift_plan(grid, region_mask, color_weaves, region_weaves, phases):
        h, w = grid.shape
        lift_plan = np.zeros((h, w), dtype=np.uint8)

        # 1. Renk Bazlı Atamalar (sadece maskesiz yerlere)
        for c_idx, weave in color_weaves.items():
            if weave is None:
                continue
            mask = (grid == c_idx) & (region_mask == 0)
            if not np.any(mask):
                continue

            px, py = phases.get(f"c_{c_idx}", (0, 0))
            shifted = np.roll(weave, shift=(py, px), axis=(0, 1))

            wh, ww = shifted.shape
            tiled = np.tile(shifted, (h // wh + 1, w // ww + 1))[:h, :w]
            lift_plan[mask] = tiled[mask]

        # 2. Bölge (Layer) Bazlı Atamalar (Override — renklerin üstüne basar)
        for r_id, weave in region_weaves.items():
            if weave is None or r_id == 0:
                continue
            mask = (region_mask == r_id)
            if not np.any(mask):
                continue

            px, py = phases.get(f"r_{r_id}", (0, 0))
            shifted = np.roll(weave, shift=(py, px), axis=(0, 1))

            wh, ww = shifted.shape
            tiled = np.tile(shifted, (h // wh + 1, w // ww + 1))[:h, :w]
            lift_plan[mask] = tiled[mask]

        return lift_plan
