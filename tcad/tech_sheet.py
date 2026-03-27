"""Technical Sheet Generator — Üretim raporu, GSM tahmini, makine özeti.

schema_version: 1.0.0
"""

import math
import time
from typing import Optional
import numpy as np

SCHEMA_VERSION = "1.0.0"


class TechnicalSheet:
    """Operatöre verilecek üretim raporu üretir."""

    @staticmethod
    def generate(doc, loom_profile=None, phys_params=None) -> dict:
        """Tam üretim raporu dict'i üretir."""
        h, w = doc.grid.shape
        sheet = {
            'schema_version': SCHEMA_VERSION,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'document_hash': hex(hash(doc.grid.tobytes()) & 0xFFFFFFFF),
        }

        # ── Pattern ──
        unique_colors = len(np.unique(doc.grid))
        sheet['pattern'] = {
            'width': w,
            'height': h,
            'repeat_x': doc.repeat_x,
            'repeat_y': doc.repeat_y,
            'total_width': w * doc.repeat_x,
            'total_height': h * doc.repeat_y,
            'color_count': unique_colors,
            'grid_bytes': doc.grid.nbytes,
        }

        # ── Weave Assignment ──
        weave_summary = {}
        for cid, weave in doc.color_weaves.items():
            if weave is not None:
                weave_summary[f"color_{cid}"] = {
                    'size': f"{weave.shape[0]}x{weave.shape[1]}",
                    'density': float(np.mean(weave)),
                }
        region_summary = {}
        for rid, weave in doc.region_weaves.items():
            if weave is not None:
                region_summary[f"region_{rid}"] = {
                    'size': f"{weave.shape[0]}x{weave.shape[1]}",
                    'density': float(np.mean(weave)),
                }
        phase_summary = {}
        for key, val in doc.weave_phases.items():
            if isinstance(val, (list, tuple)) and len(val) == 2:
                phase_summary[key] = {'x': val[0], 'y': val[1]}

        sheet['weave'] = {
            'color_weaves': weave_summary,
            'region_weaves': region_summary,
            'phase_shifts': phase_summary,
        }

        # ── Thread Plan ──
        warp_info = []
        for color, count in doc.warp_seq.sequence:
            warp_info.append({'rgb': list(color), 'count': count})
        weft_info = []
        for color, count in doc.weft_seq.sequence:
            weft_info.append({'rgb': list(color), 'count': count})

        sheet['threads'] = {
            'warp_sequence': warp_info,
            'weft_sequence': weft_info,
            'total_ends': w * doc.repeat_x,
            'total_picks': h * doc.repeat_y,
        }

        # ── Machine ──
        hook_util = min(w / max(doc.hook_count, 1), 1.0)
        needs_split = w > doc.hook_count
        sections = math.ceil(w / max(doc.hook_count, 1)) if needs_split else 1
        dead_hooks = 0
        if doc.custom_mapping is not None:
            dead_hooks = int(np.sum(doc.custom_mapping < 0))

        sheet['machine'] = {
            'hook_count': doc.hook_count,
            'hook_utilization_pct': round(hook_util * 100, 1),
            'needs_split': needs_split,
            'sections': sections,
            'dead_hooks': dead_hooks,
            'custom_mapping': doc.custom_mapping is not None,
        }

        # ── Validation Summary ──
        if getattr(doc, 'lift_plan', None) is not None:
            from tcad.validation import ValidationEngine
            errors = ValidationEngine.analyze_fabric(
                doc.lift_plan, 7, 7, region_mask=doc.region_mask)
            by_type = {}
            for e in errors:
                t = e['type']
                by_type[t] = by_type.get(t, 0) + 1
            sheet['validation'] = {
                'total_issues': len(errors),
                'by_type': by_type,
            }
        else:
            sheet['validation'] = {
                'total_issues': -1,
                'note': 'Lift plan derlenmedi — validation çalıştırılamadı',
            }

        # ── Constraint Check ──
        if loom_profile is not None:
            from tcad.constraints import ConstraintEngine
            can_export, errors, warnings, infos = \
                ConstraintEngine.is_export_ready(doc, loom_profile)
            sheet['constraints'] = {
                'profile': loom_profile.name,
                'profile_version': loom_profile.profile_version,
                'can_export': can_export,
                'blocking_errors': len(errors),
                'warnings': len(warnings),
                'infos': len(infos),
                'issues': errors + warnings + infos,
            }

        # ── Production Estimate ──
        if loom_profile is not None:
            from tcad.constraints import ConstraintEngine
            density = 20.0
            if phys_params:
                density = phys_params.get('picks_per_cm', 20.0)
            
            est = ConstraintEngine.estimate_production_time(
                h * doc.repeat_y,
                loom_profile.max_picks_per_min,
                loom_profile.typical_efficiency,
                density_picks_per_cm=density)
            sheet['production'] = est

        # ── Physical & GSM Estimate ──
        if phys_params:
            ends = phys_params.get('ends_per_cm', 40.0)
            picks = phys_params.get('picks_per_cm', 35.0)
            tex_w = phys_params.get('tex_warp', 30.0)
            tex_f = phys_params.get('tex_weft', 30.0)
            
            gsm_data = TechnicalSheet.density_gsm_estimate(
                ends, picks, yarn_tex_warp=tex_w, yarn_tex_weft=tex_f)
            
            w_cm = (w * doc.repeat_x) / max(1, ends)
            h_meters = (h * doc.repeat_y) / max(1, picks) / 100
            
            gsm_data['fabric_width_cm'] = round(w_cm, 2)
            gsm_data['fabric_length_m'] = round(h_meters, 3)
            
            # --- İplik Tüketimi (Yarn Consumption & Costing) ---
            yarn_inventory = {}
            
            for color, count in doc.warp_seq.sequence:
                idx = doc.palette.index(color) if color in doc.palette else 0
                yarn = getattr(doc, 'yarns', {}).get(idx)
                if not yarn: continue
                ends = count * doc.repeat_x
                # mass = Tex * length(m) / 1000 (gives grams). /1000 for kg.
                kg = (yarn.tex * ends * h_meters) / 1_000_000
                cost = kg * yarn.price_kg
                if yarn.name not in yarn_inventory:
                    yarn_inventory[yarn.name] = {'kg': 0.0, 'cost': 0.0, 'type': 'Warp (Kesintisiz)'}
                yarn_inventory[yarn.name]['kg'] += kg
                yarn_inventory[yarn.name]['cost'] += cost
                
            for color, count in doc.weft_seq.sequence:
                idx = doc.palette.index(color) if color in doc.palette else 0
                yarn = getattr(doc, 'yarns', {}).get(idx)
                if not yarn: continue
                picks = count * doc.repeat_y
                kg = (yarn.tex * picks * (w_cm / 100)) / 1_000_000
                cost = kg * yarn.price_kg
                if yarn.name not in yarn_inventory:
                    yarn_inventory[yarn.name] = {'kg': 0.0, 'cost': 0.0, 'type': 'Weft (Atkı)'}
                yarn_inventory[yarn.name]['kg'] += kg
                yarn_inventory[yarn.name]['cost'] += cost
                
            for k in yarn_inventory:
                yarn_inventory[k]['kg'] = round(yarn_inventory[k]['kg'], 3)
                yarn_inventory[k]['cost'] = round(yarn_inventory[k]['cost'], 2)
                
            gsm_data['yarn_inventory'] = yarn_inventory
            
            sheet['physical'] = gsm_data

        return sheet

    @staticmethod
    def density_gsm_estimate(ends_per_cm, picks_per_cm,
                              yarn_tex_warp=30.0,
                              yarn_tex_weft=30.0) -> dict:
        """Tahmini GSM (gram/m²) hesabı.

        NOT: Bu tahmindir. Crimp, finishing, shrinkage, gerçek iplik
        davranışı dahil değildir.

        Formül: GSM ≈ (ends/cm × tex_warp + picks/cm × tex_weft) / 10
        """
        if ends_per_cm <= 0 or picks_per_cm <= 0:
            return {'gsm_estimate': 0, 'confidence': 'invalid_input'}

        warp_contrib = ends_per_cm * yarn_tex_warp / 10
        weft_contrib = picks_per_cm * yarn_tex_weft / 10
        gsm = warp_contrib + weft_contrib

        return {
            'gsm_estimate': round(gsm, 1),
            'warp_contribution_pct': round(warp_contrib / max(gsm, 0.1) * 100, 1),
            'weft_contribution_pct': round(weft_contrib / max(gsm, 0.1) * 100, 1),
            'ends_per_cm': ends_per_cm,
            'picks_per_cm': picks_per_cm,
            'yarn_tex_warp': yarn_tex_warp,
            'yarn_tex_weft': yarn_tex_weft,
            'confidence': 'estimate',
            'note': 'Crimp, finishing ve shrinkage dahil değil. Gerçek GSM ±15% sapabilir.',
        }

    @staticmethod
    def export_text(sheet_dict, path) -> None:
        """Human-readable .txt rapor üretir."""
        lines = []
        lines.append("=" * 60)
        lines.append("  JACQUARD CAD — TEKNİK ÜRETİM RAPORU")
        lines.append("=" * 60)
        lines.append(f"  Tarih: {sheet_dict.get('timestamp', 'N/A')}")
        lines.append(f"  Hash: {sheet_dict.get('document_hash', 'N/A')}")
        lines.append(f"  Schema: {sheet_dict.get('schema_version', 'N/A')}")
        lines.append("")

        # Pattern
        p = sheet_dict.get('pattern', {})
        lines.append("─── DESEN ───")
        lines.append(f"  Genişlik: {p.get('width', '?')} tel")
        lines.append(f"  Yükseklik: {p.get('height', '?')} atkı")
        lines.append(f"  Tekrar: {p.get('repeat_x', 1)}x{p.get('repeat_y', 1)}")
        lines.append(f"  Toplam: {p.get('total_width', '?')}x{p.get('total_height', '?')}")
        lines.append(f"  Renk Sayısı: {p.get('color_count', '?')}")
        lines.append("")

        # Weave
        w = sheet_dict.get('weave', {})
        lines.append("─── ÖRGÜ ATAMASI ───")
        for k, v in w.get('color_weaves', {}).items():
            lines.append(f"  {k}: {v.get('size', '?')} (yoğunluk: {v.get('density', 0):.2f})")
        for k, v in w.get('region_weaves', {}).items():
            lines.append(f"  {k}: {v.get('size', '?')} (yoğunluk: {v.get('density', 0):.2f})")
        if w.get('phase_shifts'):
            lines.append("  Faz kaydırmaları:")
            for k, v in w['phase_shifts'].items():
                lines.append(f"    {k}: X={v['x']}, Y={v['y']}")
        lines.append("")

        # Machine
        m = sheet_dict.get('machine', {})
        lines.append("─── MAKİNE ───")
        lines.append(f"  Kanca: {m.get('hook_count', '?')}")
        lines.append(f"  Kullanım: %{m.get('hook_utilization_pct', 0)}")
        lines.append(f"  Dead Hook: {m.get('dead_hooks', 0)}")
        lines.append(f"  Split: {'EVET (' + str(m.get('sections', 1)) + ' head)' if m.get('needs_split') else 'HAYIR'}")
        lines.append("")

        # Validation
        v = sheet_dict.get('validation', {})
        lines.append("─── DOĞRULAMA ───")
        lines.append(f"  Toplam Sorun: {v.get('total_issues', '?')}")
        for t, c in v.get('by_type', {}).items():
            lines.append(f"    {t}: {c}")
        lines.append("")

        # Constraints
        c = sheet_dict.get('constraints', {})
        if c:
            lines.append("─── MAKİNE UYUMLULUK ───")
            lines.append(f"  Profil: {c.get('profile', '?')}")
            lines.append(f"  Export Hazır: {'EVET' if c.get('can_export') else '❌ HAYIR'}")
            lines.append(f"  Hata: {c.get('blocking_errors', 0)} | Uyarı: {c.get('warnings', 0)}")
            for issue in c.get('issues', []):
                sev = issue['severity'].upper()
                lines.append(f"  [{sev}] {issue['code']}: {issue['message']}")
            lines.append("")

        # Physical / GSM
        ph = sheet_dict.get('physical', {})
        if ph:
            lines.append("─── FİZİKSEL & KUMAŞ METRİKLERİ ───")
            lines.append(f"  Sıklık: {ph.get('ends_per_cm')} çözgü/cm x {ph.get('picks_per_cm')} atkı/cm")
            lines.append(f"  İplik Tex: Çözgü {ph.get('yarn_tex_warp')}, Atkı {ph.get('yarn_tex_weft')}")
            lines.append(f"  Kumaş Eni: {ph.get('fabric_width_cm', '?')} cm")
            lines.append(f"  Kumaş Boyu: {ph.get('fabric_length_m', '?')} metre (1 Rapor)")
            lines.append(f"  Tahmini Ağırlık: {ph.get('gsm_estimate', '?')} gr/m²")
            lines.append(f"    (Çözgü Oranı: %{ph.get('warp_contribution_pct', '?')})")
            lines.append(f"    (Atkı Oranı: %{ph.get('weft_contribution_pct', '?')})")
            
            yarns = ph.get('yarn_inventory', {})
            if yarns:
                lines.append(f"  --- İplik Bobin İhtiyacı ---")
                for name, dat in yarns.items():
                    c_str = f" | Maliyet: ${dat['cost']}" if dat['cost'] > 0 else ""
                    lines.append(f"    * {name} ({dat['type']}): {dat['kg']} KG{c_str}")

            lines.append(f"  Not: {ph.get('note', '')}")
            lines.append("")

        # Production
        pr = sheet_dict.get('production', {})
        if pr and 'hours' in pr:
            lines.append("─── ÜRETİM TAHMİNİ ───")
            lines.append(f"  Toplam Pick: {pr.get('picks', '?')}")
            lines.append(f"  RPM: {pr.get('rpm', '?')} (verim: {pr.get('efficiency', 0)*100:.0f}%)")
            lines.append(f"  Süre: {pr.get('hours', '?')} saat ({pr.get('shifts_8h', '?')} vardiya)")
            lines.append(f"  Metre/Rapor: {pr.get('meters_per_repeat', '?')}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("  RAPOR SONU")
        lines.append("=" * 60)

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
