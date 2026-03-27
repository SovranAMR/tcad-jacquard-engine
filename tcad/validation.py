"""Kumaş zekası — Float, Toroidal Wrap, İzole Bağ ve Sınır Stres analizi (V4)."""

import numpy as np


class ValidationEngine:
    """Açık risk analizi. Kopma, yırtılma ve zayıf bağ noktalarını bulur."""

    @staticmethod
    def analyze_fabric(lift_plan, max_warp=7, max_weft=7, region_mask=None):
        errors = []
        h, w = lift_plan.shape

        # 0. UNİFORM SATIR/SÜTUN KONTROLÜ (Transition-free float detection)
        # Transition-based algoritma, hiç geçiş olmayan satır/sütunları
        # yakalayamaz. Bu pre-scan tam genişlik/yükseklik float'ları yakalar.
        for y in range(h):
            row = lift_plan[y]
            if np.all(row == row[0]) and w > max_weft:
                t = "Çözgü" if row[0] == 1 else "Atkı"
                errors.append({
                    'type': f'{t} Tam Satır Float',
                    'x': 0, 'y': y,
                    'len': w, 'dir': 'weft'
                })
                if len(errors) > 500:
                    return errors

        for x in range(w):
            col = lift_plan[:, x]
            if np.all(col == col[0]) and h > max_warp:
                t = "Çözgü" if col[0] == 1 else "Atkı"
                errors.append({
                    'type': f'{t} Tam Sütun Float',
                    'x': x, 'y': 0,
                    'len': h, 'dir': 'warp'
                })
                if len(errors) > 500:
                    return errors

        # 1. RAPOR SINIRI (BOUNDARY CONTINUITY) DAHİL FLOAT KONTROLÜ
        # mode='wrap': Desenin sağını soluna, altını üstüne sarar.
        padded = np.pad(lift_plan,
                        ((max_weft, max_weft), (max_warp, max_warp)),
                        mode='wrap')

        # Atkı Atlaması (Yatay)
        diff_weft = padded[:, :-1] != padded[:, 1:]
        for y in range(max_weft, h + max_weft):
            changes = np.where(diff_weft[y])[0]
            if len(changes) < 2:
                continue
            runs = np.diff(changes)
            vals = padded[y, changes[:-1] + 1]
            bad = np.where(runs > max_weft)[0]
            for b in bad:
                real_y = y - max_weft
                real_x = (int(changes[b]) - max_warp + 1) % w
                t = "Çözgü" if vals[b] == 1 else "Atkı"
                errors.append({
                    'type': f'{t} Atlama (Rapor Dahil)',
                    'x': real_x, 'y': real_y,
                    'len': int(runs[b]), 'dir': 'weft'
                })
                if len(errors) > 500:
                    return errors

        # Çözgü Atlaması (Dikey)
        diff_warp = padded[:-1, :] != padded[1:, :]
        for x in range(max_warp, w + max_warp):
            changes = np.where(diff_warp[:, x])[0]
            if len(changes) < 2:
                continue
            runs = np.diff(changes)
            vals = padded[changes[:-1] + 1, x]
            bad = np.where(runs > max_warp)[0]
            for b in bad:
                real_x = x - max_warp
                real_y = (int(changes[b]) - max_weft + 1) % h
                t = "Çözgü" if vals[b] == 1 else "Atkı"
                errors.append({
                    'type': f'{t} Atlama (Rapor Dahil)',
                    'x': real_x, 'y': real_y,
                    'len': int(runs[b]), 'dir': 'warp'
                })
                if len(errors) > 500:
                    return errors

        # 2. İZOLE BAĞ NOKTALARI (WEAK STRUCTURE / PINHOLE)
        p = np.pad(lift_plan, 1, mode='wrap')
        neighbors = (p[:-2, 1:-1] + p[2:, 1:-1] +
                     p[1:-1, :-2] + p[1:-1, 2:])

        iso_warp = (lift_plan == 1) & (neighbors == 0)
        iso_weft = (lift_plan == 0) & (neighbors == 4)

        for y, x in np.argwhere(iso_warp):
            errors.append({
                'type': 'İzole Bağ (Çözgü)', 'x': int(x), 'y': int(y),
                'len': 1, 'dir': 'point'
            })
        for y, x in np.argwhere(iso_weft):
            errors.append({
                'type': 'İzole Bağ (Atkı)', 'x': int(x), 'y': int(y),
                'len': 1, 'dir': 'point'
            })

        # 3. MOTİF KENARI STRES ANALİZİ (EDGE CONTINUITY)
        if region_mask is not None:
            # Dikey sınırlar
            bounds_x = region_mask[:, :-1] != region_mask[:, 1:]
            same_lift_x = lift_plan[:, :-1] == lift_plan[:, 1:]
            stress_x = bounds_x & same_lift_x
            for y, x in np.argwhere(stress_x):
                errors.append({
                    'type': 'Sınır Kırılması (Dikey)',
                    'x': int(x), 'y': int(y), 'len': 2, 'dir': 'edge_x'
                })
                if len(errors) > 500:
                    return errors

            # Yatay sınırlar
            bounds_y = region_mask[:-1, :] != region_mask[1:, :]
            same_lift_y = lift_plan[:-1, :] == lift_plan[1:, :]
            stress_y = bounds_y & same_lift_y
            for y, x in np.argwhere(stress_y):
                errors.append({
                    'type': 'Sınır Kırılması (Yatay)',
                    'x': int(x), 'y': int(y), 'len': 2, 'dir': 'edge_y'
                })
                if len(errors) > 500:
                    return errors

        return errors[:500]

    @staticmethod
    def auto_fix_floats(lift_plan, max_warp=7, max_weft=7, region_mask=None) -> tuple[np.ndarray, int]:
        """Tüm hatalı atlamaları estetik Saten/Dimi bağlama kurallarına göre düzeltir.
        Geriye (düzeltilmiş_plan, toplam_düzeltme_sayısı) döndürür."""

        fixed = lift_plan.copy()
        flipped_mask = np.zeros_like(fixed, dtype=bool)
        total_fixes = 0
        h, w = fixed.shape

        while True:
            errors = ValidationEngine.analyze_fabric(fixed, max_warp, max_weft, region_mask)
            flips = set()

            for e in errors:
                if 'Atlama' not in e['type'] and 'Float' not in e['type']:
                    continue
                if e['dir'] not in ('warp', 'weft'):
                    continue

                dx = 1 if e['dir'] == 'weft' else 0
                dy = 1 if e['dir'] == 'warp' else 0

                # Kırmızı Takım Algoritması: Rastgele düğüm yerine estetik (Twill/Satin) adım kaydırma
                best_mid = None
                
                # Float boyunca estetik bağlama noktası ara (7'li veya 5'li saten/dimi adımı)
                for i in range(1, e['len'] - 1):
                    fx = (e['x'] + dx * i) % w
                    fy = (e['y'] + dy * i) % h
                    
                    if not flipped_mask[fy, fx]:
                        if e['dir'] == 'warp':
                            if (fy + fx * 3) % 7 == 0:  # 7'li Saten/Dimi kaydırması
                                best_mid = i
                                break
                        else:
                            if (fx + fy * 3) % 7 == 0:
                                best_mid = i
                                break

                # Eğer estetik kurala uyan nokta bulunamadıysa VEYA daha önce değiştirilmişse, ortadan kır (Yedek Plan)
                if best_mid is None:
                    mid = e['len'] // 2
                    mid_offset = 0
                    while True:
                        test_mid = mid + mid_offset
                        if test_mid <= 0 or test_mid >= e['len']:
                            break

                        fx = (e['x'] + dx * test_mid) % w
                        fy = (e['y'] + dy * test_mid) % h

                        if not flipped_mask[fy, fx]:
                            best_mid = test_mid
                            break

                        if mid_offset <= 0:
                            mid_offset = -mid_offset + 1
                        else:
                            mid_offset = -mid_offset

                if best_mid is not None:
                    fx = (e['x'] + dx * best_mid) % w
                    fy = (e['y'] + dy * best_mid) % h
                    flips.add((fy, fx))

            if not flips:
                break

            for fy, fx in flips:
                fixed[fy, fx] = 1 - fixed[fy, fx]
                flipped_mask[fy, fx] = True
                total_fixes += 1

        return fixed, total_fixes
