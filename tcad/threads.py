"""İplik planlama motoru — RLE çözgü/atkı dizilimi ve 32-bit kumaş simülatörü."""

import numpy as np


class ThreadSequence:
    """Run-Length Encoding (RLE) mantığıyla Çözgü ve Atkı dizilimi."""

    def __init__(self, default_color=(220, 220, 220)):
        # Format: [(R,G,B), Tel_Adedi]
        self.sequence = [(default_color, 1)]

    def generate(self, total_length):
        """Dizilimi makine ölçüsüne kadar sonsuz tekrarla (Repeat Order) yayar."""
        if not self.sequence:
            return np.full((total_length, 3), 128, dtype=np.uint8)

        colors, counts = [], []
        for color, count in self.sequence:
            colors.append(color)
            counts.append(count)

        colors_arr = np.array(colors, dtype=np.uint8)
        counts_arr = np.array(counts, dtype=np.int32)

        # Dizilimi aç (Örn: 2 Kırmızı -> K, K)
        pattern = np.repeat(colors_arr, counts_arr, axis=0)
        if len(pattern) == 0:
            return np.full((total_length, 3), 128, dtype=np.uint8)
        repeats = (total_length // len(pattern)) + 1
        return np.tile(pattern, (repeats, 1))[:total_length]


class FabricSimulator:
    """Lift planı ve iplik dizilimlerini alarak Gerçek Kumaş RGB matrisi üretir."""

    @staticmethod
    def render_fabric(lift_plan, warp_seq: ThreadSequence, weft_seq: ThreadSequence, enable_3d=True):
        h, w = lift_plan.shape
        warp_colors = warp_seq.generate(w)  # (w, 3)
        weft_colors = weft_seq.generate(h)  # (h, 3)

        # Vektörel Broadcasting: 1D iplikleri 2D matris uzayına yay
        warp_grid = np.broadcast_to(warp_colors, (h, w, 3))
        weft_grid = np.broadcast_to(weft_colors[:, None, :], (h, w, 3))

        # Lift plan 1 = Çözgü görünür, 0 = Atkı görünür
        mask = lift_plan == 1
        fabric = np.where(mask[..., None], warp_grid, weft_grid).astype(np.float32)

        if enable_3d:
            # Vektörel Bump Mapping / Shader Simulasyonu
            shading = np.ones((h, w), dtype=np.float32)
            
            # Türevler (Geçiş / Dipping noktaları)
            diff_x = np.abs(np.diff(lift_plan.astype(np.float32), axis=1))
            diff_y = np.abs(np.diff(lift_plan.astype(np.float32), axis=0))
            
            # Ambient Occlusion (İpliklerin kesişim çukurlarına düşen gölgeler)
            ao = np.zeros((h, w), dtype=np.float32)
            ao[:, :-1] += diff_x * 0.35
            ao[:, 1:]  += diff_x * 0.35
            ao[:-1, :] += diff_y * 0.35
            ao[1:, :]  += diff_y * 0.35
            
            # Yüksek (Atlama Yapan) Noktalara Yansıma (Specular Highlight)
            # ao == 0 ise iplik düz ilerliyordur (float), ışığı daha çok yansıtır.
            specular = np.where(ao == 0, 1.15, 1.0)
            
            shading = (shading * specular) - ao
            shading = np.clip(shading, 0.4, 1.4)
            
            fabric = fabric * shading[..., None]

        fabric = np.clip(fabric, 0, 255)

        # 32-bit RGBA hizalama (QImage çökmesini engeller)
        rgba = np.empty((h, w, 4), dtype=np.uint8)
        rgba[:, :, :3] = fabric.astype(np.uint8)
        rgba[:, :, 3] = 255

        return np.ascontiguousarray(rgba, dtype=np.uint8)
