"""
MALFORMED INPUT — Bozuk dosya, hostile parametreler, sınır değerler.
"""
import os, sys, tempfile, zipfile, json, io
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from tcad.domain import Document
from tcad.fileio import save_project, load_project, import_image, export_png
from tcad.weaves import WeaveLibrary, WeaveEngine
from tcad.validation import ValidationEngine
from tcad.mapping import HookMapping
from tcad.threads import ThreadSequence, FabricSimulator


class TestCorruptTcad:
    def test_not_a_zip(self):
        path = os.path.join(tempfile.gettempdir(), "not_zip.tcad")
        with open(path, 'wb') as f:
            f.write(b'GARBAGE DATA NOT A ZIP')
        doc = Document(10, 10)
        with pytest.raises(Exception):
            load_project(doc, path)
        os.remove(path)

    def test_missing_meta_json(self):
        """meta.json yok — hata vermeli."""
        path = os.path.join(tempfile.gettempdir(), "no_meta.tcad")
        buf = io.BytesIO()
        np.save(buf, np.zeros((10, 10), dtype=np.uint8))
        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('data.npy', buf.getvalue())
        doc = Document(10, 10)
        with pytest.raises(Exception):
            load_project(doc, path)
        os.remove(path)

    def test_missing_data_npy(self):
        """data.npy yok — hata vermeli."""
        path = os.path.join(tempfile.gettempdir(), "no_data.tcad")
        meta = {'w': 10, 'h': 10, 'rx': 1, 'ry': 1, 'pal': [(0, 0, 0)] * 256}
        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('meta.json', json.dumps(meta))
        doc = Document(10, 10)
        with pytest.raises(Exception):
            load_project(doc, path)
        os.remove(path)

    def test_mismatched_shape(self):
        """meta.json width=100 ama data.npy 10x10 — çelişki."""
        path = os.path.join(tempfile.gettempdir(), "mismatch.tcad")
        meta = {'w': 100, 'h': 100, 'rx': 1, 'ry': 1,
                'pal': [(0, 0, 0)] * 256}
        buf = io.BytesIO()
        np.save(buf, np.zeros((10, 10), dtype=np.uint8))
        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('meta.json', json.dumps(meta))
            zf.writestr('data.npy', buf.getvalue())
        doc = Document(5, 5)
        with pytest.raises(ValueError, match="RED TEAM GUARD"):
            load_project(doc, path)
        os.remove(path)

    def test_corrupt_npy_data(self):
        """data.npy bozuk binary — hata vermeli."""
        path = os.path.join(tempfile.gettempdir(), "bad_npy.tcad")
        meta = {'w': 10, 'h': 10, 'rx': 1, 'ry': 1, 'pal': [(0, 0, 0)] * 256}
        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('meta.json', json.dumps(meta))
            zf.writestr('data.npy', b'NOT VALID NPY DATA')
        doc = Document(5, 5)
        with pytest.raises(Exception):
            load_project(doc, path)
        os.remove(path)

    def test_empty_palette(self):
        """Boş palette — crash etmemeli."""
        path = os.path.join(tempfile.gettempdir(), "empty_pal.tcad")
        meta = {'w': 10, 'h': 10, 'rx': 1, 'ry': 1, 'pal': []}
        buf = io.BytesIO()
        np.save(buf, np.zeros((10, 10), dtype=np.uint8))
        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('meta.json', json.dumps(meta))
            zf.writestr('data.npy', buf.getvalue())
        doc = Document(5, 5)
        load_project(doc, path)
        assert doc.palette == []  # loaded as empty


class TestHostileParameters:
    def test_zero_size_document(self):
        """0x0 document — crash etmemeli."""
        try:
            doc = Document(0, 0)
            assert doc.grid.shape == (0, 0)
        except Exception as e:
            pytest.fail(f"0x0 document crash: {e}")

    def test_huge_repeat(self):
        """repeat_x=1000 — memory allocation kontrolü."""
        doc = Document(10, 10)
        doc.repeat_x = 1000
        doc.repeat_y = 1000
        # Bu sadece değer ataması; gerçek bellek tahsisi render'da olur
        assert doc.repeat_x == 1000

    def test_negative_mapping_array(self):
        """Tamamen -1 mapping — crash etmemeli."""
        lp = np.ones((5, 5), dtype=np.uint8)
        mapping = np.full(5, -1, dtype=np.int64)
        m_plan = HookMapping.apply_fast(lp, mapping, 10)
        assert np.all(m_plan == 0), "Tüm dead hook → boş plan"

    def test_single_pixel_document(self):
        """1x1 document tüm pipeline."""
        doc = Document(1, 1)
        doc.grid[0, 0] = 1
        doc.color_weaves[1] = WeaveLibrary.plain()
        lp = WeaveEngine.build_lift_plan(
            doc.grid, doc.region_mask,
            doc.color_weaves, doc.region_weaves, {})
        assert lp.shape == (1, 1)
        fabric = FabricSimulator.render_fabric(lp, doc.warp_seq, doc.weft_seq)
        assert fabric.shape == (1, 1, 4)
        errors = ValidationEngine.analyze_fabric(lp, 7, 7)
        # 1x1 pattern — no floats possible at this size
        assert isinstance(errors, list)

    def test_weave_larger_than_pattern(self):
        """10x10 örgü, 5x5 desen — tile sorunsuz çalışmalı."""
        doc = Document(5, 5)
        doc.grid[:, :] = 1
        big_weave = np.eye(10, dtype=np.uint8)
        doc.color_weaves[1] = big_weave
        lp = WeaveEngine.build_lift_plan(
            doc.grid, doc.region_mask,
            doc.color_weaves, doc.region_weaves, {})
        assert lp.shape == (5, 5)

    def test_empty_thread_sequence_fabric(self):
        """Boş thread sequence ile fabric render — crash etmemeli."""
        lp = np.array([[1, 0], [0, 1]], dtype=np.uint8)
        warp = ThreadSequence((100, 100, 100))
        warp.sequence.clear()
        weft = ThreadSequence((50, 50, 50))
        weft.sequence.clear()
        fabric = FabricSimulator.render_fabric(lp, warp, weft)
        assert fabric.shape == (2, 2, 4)


class TestImageImport:
    def test_import_nonexistent_file(self):
        doc = Document(10, 10)
        with pytest.raises(Exception):
            import_image(doc, "/nonexistent/path/foo.png")

    def test_import_non_image_file(self):
        path = os.path.join(tempfile.gettempdir(), "not_image.png")
        with open(path, 'w') as f:
            f.write("this is not an image")
        doc = Document(10, 10)
        with pytest.raises(Exception):
            import_image(doc, path)
        os.remove(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
