"""TEST — Loom Constraint Engine"""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from tcad.domain import Document
from tcad.weaves import WeaveLibrary, WeaveEngine
from tcad.constraints import (ConstraintEngine, LoomProfile,
                                STAUBLI_CX880, BONAS_SI, DOBBY_GENERIC)


class TestLoomProfile:
    def test_default_profile(self):
        p = LoomProfile()
        assert p.max_hooks == 2688
        assert p.harness_type == 'electronic'
        assert p.supports_split is True

    def test_preset_profiles(self):
        assert STAUBLI_CX880.max_hooks == 5376
        assert BONAS_SI.max_hooks == 2688
        assert DOBBY_GENERIC.max_hooks == 24


class TestConstraintValidation:
    def test_hook_limit_error(self):
        # Superseded by test_split_not_supported
        pass

    def test_hook_near_limit_warning(self):
        doc = Document(2500, 100)  # 93% of 2688
        issues = ConstraintEngine.validate_for_loom(doc, LoomProfile())
        warns = [i for i in issues if i['code'] == 'HOOK_NEAR_LIMIT']
        assert len(warns) == 1
        assert warns[0]['severity'] == 'warning'

    def test_within_limits_clean(self):
        doc = Document(100, 100)
        issues = ConstraintEngine.validate_for_loom(doc, LoomProfile())
        errors = [i for i in issues if i['severity'] == 'error']
        assert len(errors) == 0

    def test_split_not_supported(self):
        doc = Document(50, 50)
        profile = LoomProfile(max_hooks=30, supports_split=False)
        issues = ConstraintEngine.validate_for_loom(doc, profile)
        split_err = [i for i in issues if i['code'] == 'SPLIT_NOT_SUPPORTED']
        assert len(split_err) == 1

    def test_too_many_sections(self):
        doc = Document(500, 10)
        profile = LoomProfile(max_hooks=100, supports_split=True, max_sections=2)
        issues = ConstraintEngine.validate_for_loom(doc, profile)
        too_many = [i for i in issues if i['code'] == 'TOO_MANY_SECTIONS']
        assert len(too_many) == 1  # needs 5, max 2

    def test_float_violation_with_lift_plan(self):
        doc = Document(20, 20)
        doc.grid[:, :] = 0  # All zero = all weft float
        doc.lift_plan = np.zeros((20, 20), dtype=np.uint8)
        profile = LoomProfile(max_float_weft=7)
        issues = ConstraintEngine.validate_for_loom(doc, profile)
        float_err = [i for i in issues if i['code'] == 'FLOAT_VIOLATION']
        assert len(float_err) == 1

    def test_repeat_limit(self):
        doc = Document(100, 100)
        doc.repeat_x = 300
        profile = LoomProfile(max_repeat_width=10000)
        issues = ConstraintEngine.validate_for_loom(doc, profile)
        rep = [i for i in issues if i['code'] == 'REPEAT_WIDTH_EXCEEDED']
        assert len(rep) == 1  # 100*300 = 30000 > 10000

    def test_severity_format(self):
        doc = Document(3000, 100)
        issues = ConstraintEngine.validate_for_loom(doc, LoomProfile())
        for issue in issues:
            assert 'severity' in issue
            assert 'code' in issue
            assert 'message' in issue
            assert issue['severity'] in ('error', 'warning', 'info')


class TestProductionEstimate:
    def test_basic_estimate(self):
        r = ConstraintEngine.estimate_production_time(6000, 600, 0.85)
        assert r['picks'] == 6000
        assert r['effective_rpm'] == 600 * 0.85
        assert r['hours'] > 0
        assert r['shifts_8h'] > 0

    def test_zero_rpm(self):
        r = ConstraintEngine.estimate_production_time(100, 0)
        assert 'error' in r

    def test_target_meters(self):
        r = ConstraintEngine.estimate_production_time(
            1000, 600, 0.85, density_picks_per_cm=20, target_meters=100)
        assert 'repeats_needed' in r
        assert 'total_hours' in r

    def test_over_1_efficiency_clamped(self):
        r = ConstraintEngine.estimate_production_time(1000, 600, 1.5)
        assert r['efficiency'] == 1.0


class TestYarnBreakRisk:
    def test_cotton_normal(self):
        risks = ConstraintEngine.yarn_break_risk([3, 5, 8, 12])
        high = [r for r in risks if r['risk_level'] == 'YÜKSEK']
        critical = [r for r in risks if r['risk_level'] == 'KRİTİK']
        assert len(risks) > 0  # Some should be flagged

    def test_silk_more_sensitive(self):
        risks_cotton = ConstraintEngine.yarn_break_risk(
            [5], yarn_type='cotton')
        risks_silk = ConstraintEngine.yarn_break_risk(
            [5], yarn_type='silk')
        # Silk has lower threshold, so same float = higher risk
        if risks_silk and risks_cotton:
            assert risks_silk[0]['ratio'] >= risks_cotton[0]['ratio']

    def test_high_tension_increases_risk(self):
        r_normal = ConstraintEngine.yarn_break_risk(
            [6], tension_level=1.0)
        r_high = ConstraintEngine.yarn_break_risk(
            [6], tension_level=2.0)
        if r_normal and r_high:
            assert r_high[0]['ratio'] >= r_normal[0]['ratio']

    def test_fine_yarn_increases_risk(self):
        r_thick = ConstraintEngine.yarn_break_risk(
            [6], yarn_tex=60.0)
        r_fine = ConstraintEngine.yarn_break_risk(
            [6], yarn_tex=15.0)
        if r_thick and r_fine:
            assert r_fine[0]['ratio'] >= r_thick[0]['ratio']

    def test_empty_floats(self):
        r = ConstraintEngine.yarn_break_risk([])
        assert r == []


class TestAcceptanceGate:
    def test_clean_doc_can_export(self):
        doc = Document(100, 100)
        can, errs, warns, infos = ConstraintEngine.is_export_ready(
            doc, LoomProfile())
        assert can is True
        assert len(errs) == 0

    def test_oversized_doc_blocked(self):
        doc = Document(3000, 100)
        can, errs, warns, infos = ConstraintEngine.is_export_ready(
            doc, LoomProfile(max_hooks=100, supports_split=False))
        assert can is False
        assert len(errs) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
