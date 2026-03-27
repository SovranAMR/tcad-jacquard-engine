"""Loom Constraint Engine — Makine fiziksel sınırları, üretim tahmini, risk analizi.

severity tabanlı standart issue objesi:
  {'severity': 'error'|'warning'|'info',
   'code': str,
   'message': str,
   'location': str,
   'suggestion': str}
"""

import math
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


SCHEMA_VERSION = "1.0.0"


@dataclass
class LoomProfile:
    """Makine profili — tüm fiziksel sınırlar tek yerde."""

    name: str = "Generic Jacquard"
    profile_version: str = "1.0"

    # Hook / Harness
    max_hooks: int = 2688
    harness_type: str = 'electronic'  # 'electronic' | 'dobby' | 'cam'
    allowed_harness_types: tuple = ('electronic',)

    # Pattern limits
    max_repeat_width: int = 20000
    max_repeat_height: int = 20000
    max_pattern_bytes: int = 256 * 1024 * 1024  # 256MB

    # Float limits
    max_float_warp: int = 7
    max_float_weft: int = 7
    min_bind_frequency: int = 8  # Her N piksel arası en az 1 bağ

    # Density (tel/cm)
    min_density_warp: float = 8.0
    max_density_warp: float = 120.0
    min_density_weft: float = 8.0
    max_density_weft: float = 100.0

    # Speed
    max_picks_per_min: int = 600
    typical_efficiency: float = 0.85

    # Sectional
    supports_split: bool = True
    max_sections: int = 10


# ── Preset Profiles ────────────────────────────────────────

STAUBLI_CX880 = LoomProfile(
    name="Stäubli CX880",
    max_hooks=5376,
    harness_type='electronic',
    max_float_warp=9,
    max_float_weft=9,
    max_picks_per_min=800,
    supports_split=True,
    max_sections=4,
)

BONAS_SI = LoomProfile(
    name="Bonas Si",
    max_hooks=2688,
    harness_type='electronic',
    max_float_warp=7,
    max_float_weft=7,
    max_picks_per_min=600,
    supports_split=True,
    max_sections=8,
)

DOBBY_GENERIC = LoomProfile(
    name="Generic Dobby",
    max_hooks=24,
    harness_type='dobby',
    allowed_harness_types=('dobby',),
    max_float_warp=5,
    max_float_weft=5,
    max_picks_per_min=400,
    supports_split=False,
    max_sections=1,
)


def _issue(severity, code, message, location="", suggestion=""):
    return {
        'severity': severity,
        'code': code,
        'message': message,
        'location': location,
        'suggestion': suggestion,
    }


class ConstraintEngine:
    """Export öncesi doğrulama — makine profili ile deseni karşılaştırır."""

    @staticmethod
    def validate_for_loom(doc, profile: LoomProfile) -> list:
        """Tüm constraint kontrollerini çalıştırır. Severity-tabanlı issue listesi döndürür."""
        issues = []
        h, w = doc.grid.shape

        # ── Hook limit ──
        if w <= profile.max_hooks and w > profile.max_hooks * 0.9:
            issues.append(_issue(
                'warning', 'HOOK_NEAR_LIMIT',
                f"Desen genişliği ({w}) kanca limitinin %90'ına yakın ({profile.max_hooks}).",
                f"width={w}",
                "Başlık değişikliği durumunda sorun çıkabilir."
            ))

        # ── Pattern size ──
        pattern_bytes = h * w
        if pattern_bytes > profile.max_pattern_bytes:
            issues.append(_issue(
                'error', 'PATTERN_TOO_LARGE',
                f"Desen boyutu ({pattern_bytes / 1e6:.1f}MB) makine bellek limitini aşıyor.",
                f"size={pattern_bytes}",
                "Deseni küçültün veya rapor boyutunu azaltın."
            ))

        # ── Repeat limits ──
        if w * doc.repeat_x > profile.max_repeat_width:
            issues.append(_issue(
                'error', 'REPEAT_WIDTH_EXCEEDED',
                f"Toplam genişlik ({w * doc.repeat_x}) makine repeat limitini aşıyor.",
            ))
        if h * doc.repeat_y > profile.max_repeat_height:
            issues.append(_issue(
                'error', 'REPEAT_HEIGHT_EXCEEDED',
                f"Toplam yükseklik ({h * doc.repeat_y}) makine repeat limitini aşıyor.",
            ))

        # ── Harness type ──
        if profile.harness_type not in profile.allowed_harness_types:
            issues.append(_issue(
                'warning', 'HARNESS_MISMATCH',
                f"Profil harness tipi ({profile.harness_type}) izin verilen listede değil.",
            ))

        # ── Sectional split feasibility ──
        if w > profile.max_hooks and not profile.supports_split:
            issues.append(_issue(
                'error', 'SPLIT_NOT_SUPPORTED',
                f"Kanca limiti aşılıyor ama makine sectional split desteklemiyor.",
                suggestion="Farklı makine profili seçin veya deseni daraltın."
            ))
        elif w > profile.max_hooks and profile.supports_split:
            sections_needed = math.ceil(w / profile.max_hooks)
            if sections_needed > profile.max_sections:
                issues.append(_issue(
                    'error', 'TOO_MANY_SECTIONS',
                    f"{sections_needed} section gerekli ama makine max {profile.max_sections} destekliyor.",
                ))
            else:
                issues.append(_issue(
                    'info', 'SPLIT_REQUIRED',
                    f"Desen {sections_needed} head'e bölünecek.",
                ))

        # ── Float validation (if lift_plan exists) ──
        if getattr(doc, 'lift_plan', None) is not None:
            from tcad.validation import ValidationEngine
            errors = ValidationEngine.analyze_fabric(
                doc.lift_plan,
                profile.max_float_warp,
                profile.max_float_weft,
                region_mask=doc.region_mask)
            float_count = len([e for e in errors
                               if 'Atlama' in e['type'] or 'Float' in e['type']])
            iso_count = len([e for e in errors if 'İzole' in e['type']])
            edge_count = len([e for e in errors if 'Sınır' in e['type']])

            if float_count > 0:
                issues.append(_issue(
                    'error', 'FLOAT_VIOLATION',
                    f"{float_count} adet float limiti ihlali tespit edildi.",
                    suggestion=f"Warp max={profile.max_float_warp}, weft max={profile.max_float_weft} için örgü düzenleyin."
                ))
            if iso_count > 0:
                issues.append(_issue(
                    'warning', 'ISOLATED_BINDS',
                    f"{iso_count} adet izole bağ noktası tespit edildi.",
                    suggestion="Zayıf yapı riski. Ek bağ noktaları ekleyin."
                ))
            if edge_count > 0:
                issues.append(_issue(
                    'warning', 'EDGE_STRESS',
                    f"{edge_count} adet sınır stres noktası tespit edildi.",
                    suggestion="Region sınırlarında örgü geçişi gözden geçirilmeli."
                ))

        return issues

    @staticmethod
    def estimate_production_time(picks, rpm, efficiency=0.85,
                                  density_picks_per_cm=20.0,
                                  target_meters=None) -> dict:
        """Üretim süresi ve metre tahmini."""
        if rpm <= 0:
            return {'error': 'RPM sıfır veya negatif olamaz'}

        eff = max(0.01, min(1.0, efficiency))
        effective_rpm = rpm * eff
        minutes = picks / effective_rpm
        hours = minutes / 60
        shifts_8h = hours / 8

        # Metre hesabı
        cm_per_repeat = picks / max(density_picks_per_cm, 0.1)
        meters_per_repeat = cm_per_repeat / 100

        result = {
            'picks': picks,
            'rpm': rpm,
            'efficiency': eff,
            'effective_rpm': effective_rpm,
            'minutes': round(minutes, 1),
            'hours': round(hours, 2),
            'shifts_8h': round(shifts_8h, 2),
            'meters_per_repeat': round(meters_per_repeat, 3),
        }

        if target_meters is not None and target_meters > 0:
            repeats_needed = math.ceil(target_meters / max(meters_per_repeat, 0.001))
            total_picks = repeats_needed * picks
            total_minutes = total_picks / effective_rpm
            result['target_meters'] = target_meters
            result['repeats_needed'] = repeats_needed
            result['total_picks'] = total_picks
            result['total_hours'] = round(total_minutes / 60, 2)

        return result

    @staticmethod
    def yarn_break_risk(float_lengths, yarn_type='cotton',
                        yarn_tex=30.0, tension_level=1.0,
                        weave_density=1.0) -> list:
        """İplik kopma risk skoru.

        Args:
            float_lengths: float uzunlukları listesi
            yarn_type: 'cotton', 'polyester', 'silk', 'viscose'
            yarn_tex: iplik inceliği (tex)
            tension_level: gerginlik çarpanı (1.0 = normal)
            weave_density: örgü yoğunluğu çarpanı
        """
        # İplik tipi bazlı temel kırılma eşikleri
        type_thresholds = {
            'cotton': 6,
            'polyester': 9,
            'silk': 4,
            'viscose': 5,
            'wool': 5,
        }
        base_threshold = type_thresholds.get(yarn_type, 6)

        # tex etkisi: ince iplik daha kolay kopar
        tex_factor = max(0.3, min(2.0, 30.0 / max(yarn_tex, 1.0)))

        # Gerginlik etkisi
        tension_factor = max(0.5, min(3.0, tension_level))

        effective_threshold = base_threshold / (tex_factor * tension_factor)

        risks = []
        for length in float_lengths:
            ratio = length / max(effective_threshold, 0.1)
            if ratio > 2.0:
                sev = 'error'
                risk = 'KRİTİK'
            elif ratio > 1.0:
                sev = 'warning'
                risk = 'YÜKSEK'
            elif ratio > 0.7:
                sev = 'info'
                risk = 'ORTA'
            else:
                continue  # Düşük risk — raporlama

            risks.append({
                'severity': sev,
                'float_length': length,
                'risk_level': risk,
                'ratio': round(ratio, 2),
                'effective_threshold': round(effective_threshold, 1),
                'suggestion': f"{yarn_type} {yarn_tex}tex @ tension {tension_level}x: "
                              f"float {length} > eşik {effective_threshold:.0f}"
            })

        return risks

    @staticmethod
    def is_export_ready(doc, profile: LoomProfile) -> tuple:
        """Acceptance gate — export öncesi tek karar noktası.

        Returns:
            (can_export: bool, blocking_errors: list, warnings: list)
        """
        issues = ConstraintEngine.validate_for_loom(doc, profile)
        errors = [i for i in issues if i['severity'] == 'error']
        warnings = [i for i in issues if i['severity'] == 'warning']
        infos = [i for i in issues if i['severity'] == 'info']
        return len(errors) == 0, errors, warnings, infos
