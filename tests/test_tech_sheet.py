"""TEST — Technical Sheet Generator"""
import os, sys, tempfile
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from tcad.domain import Document
from tcad.weaves import WeaveLibrary, WeaveEngine
from tcad.tech_sheet import TechnicalSheet
from tcad.constraints import LoomProfile, STAUBLI_CX880


class TestSheetGeneration:
    def test_basic_sheet_keys(self):
        doc = Document(100, 100)
        sheet = TechnicalSheet.generate(doc)
        assert 'schema_version' in sheet
        assert 'timestamp' in sheet
        assert 'document_hash' in sheet
        assert 'pattern' in sheet
        assert 'weave' in sheet
        assert 'threads' in sheet
        assert 'machine' in sheet
        assert 'validation' in sheet

    def test_pattern_dimensions(self):
        doc = Document(200, 150)
        doc.repeat_x = 3
        sheet = TechnicalSheet.generate(doc)
        assert sheet['pattern']['width'] == 200
        assert sheet['pattern']['height'] == 150
        assert sheet['pattern']['total_width'] == 600

    def test_weave_summary(self):
        doc = Document(50, 50)
        doc.grid[:, :] = 1
        doc.color_weaves[1] = WeaveLibrary.plain()
        sheet = TechnicalSheet.generate(doc)
        assert 'color_1' in sheet['weave']['color_weaves']

    def test_region_weave_summary(self):
        doc = Document(50, 50)
        doc.region_weaves[1] = WeaveLibrary.satin(5, 2)
        sheet = TechnicalSheet.generate(doc)
        assert 'region_1' in sheet['weave']['region_weaves']

    def test_phase_shift_in_sheet(self):
        doc = Document(50, 50)
        doc.weave_phases = {"c_1": (2, 3)}
        sheet = TechnicalSheet.generate(doc)
        assert 'c_1' in sheet['weave']['phase_shifts']
        assert sheet['weave']['phase_shifts']['c_1']['x'] == 2

    def test_validation_with_lift_plan(self):
        doc = Document(20, 20)
        doc.grid[:, :] = 1
        doc.color_weaves[1] = WeaveLibrary.plain()
        doc.lift_plan = WeaveEngine.build_lift_plan(
            doc.grid, doc.region_mask,
            doc.color_weaves, doc.region_weaves, {})
        sheet = TechnicalSheet.generate(doc)
        assert sheet['validation']['total_issues'] >= 0

    def test_validation_without_lift_plan(self):
        doc = Document(20, 20)
        sheet = TechnicalSheet.generate(doc)
        assert sheet['validation']['total_issues'] == -1

    def test_constraint_integration(self):
        doc = Document(100, 100)
        sheet = TechnicalSheet.generate(doc, loom_profile=STAUBLI_CX880)
        assert 'constraints' in sheet
        assert sheet['constraints']['profile'] == 'Stäubli CX880'
        assert 'can_export' in sheet['constraints']

    def test_production_estimate_in_sheet(self):
        doc = Document(100, 100)
        sheet = TechnicalSheet.generate(doc, loom_profile=STAUBLI_CX880)
        assert 'production' in sheet
        assert 'hours' in sheet['production']

    def test_split_doc_machine_info(self):
        doc = Document(3000, 100)
        sheet = TechnicalSheet.generate(doc)
        assert sheet['machine']['needs_split'] is True
        assert sheet['machine']['sections'] > 1

    def test_dead_hooks_tracked(self):
        doc = Document(100, 100)
        doc.custom_mapping = np.array([0]*50 + [-1]*50, dtype=np.int32)
        sheet = TechnicalSheet.generate(doc)
        assert sheet['machine']['dead_hooks'] == 50

    def test_empty_doc_no_crash(self):
        doc = Document(1, 1)
        sheet = TechnicalSheet.generate(doc)
        assert sheet['pattern']['width'] == 1

    def test_malformed_thread_safe(self):
        doc = Document(20, 20)
        doc.warp_seq.sequence.clear()
        doc.weft_seq.sequence.clear()
        sheet = TechnicalSheet.generate(doc)
        assert sheet['threads']['warp_sequence'] == []


class TestGSMEstimate:
    def test_known_calculation(self):
        # 40 ends/cm * 30tex + 30 picks/cm * 30tex = 1200+900 /10 = 210
        r = TechnicalSheet.density_gsm_estimate(40, 30, 30, 30)
        assert r['gsm_estimate'] == 210.0
        assert r['confidence'] == 'estimate'

    def test_label_is_estimate(self):
        r = TechnicalSheet.density_gsm_estimate(20, 20)
        assert 'estimate' in r['confidence']
        assert 'Crimp' in r['note']

    def test_zero_input(self):
        r = TechnicalSheet.density_gsm_estimate(0, 20)
        assert r['gsm_estimate'] == 0
        assert r['confidence'] == 'invalid_input'


class TestTextExport:
    def test_export_creates_file(self):
        doc = Document(100, 100)
        sheet = TechnicalSheet.generate(doc, loom_profile=STAUBLI_CX880)
        path = os.path.join(tempfile.gettempdir(), "test_report.txt")
        TechnicalSheet.export_text(sheet, path)
        assert os.path.exists(path)
        with open(path, 'r') as f:
            content = f.read()
        assert 'TEKNİK ÜRETİM RAPORU' in content
        assert 'DESEN' in content
        assert 'MAKİNE' in content
        os.remove(path)

    def test_export_contains_constraint_info(self):
        doc = Document(100, 100)
        sheet = TechnicalSheet.generate(doc, loom_profile=STAUBLI_CX880)
        path = os.path.join(tempfile.gettempdir(), "test_report2.txt")
        TechnicalSheet.export_text(sheet, path)
        with open(path, 'r') as f:
            content = f.read()
        assert 'UYUMLULUK' in content
        os.remove(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
