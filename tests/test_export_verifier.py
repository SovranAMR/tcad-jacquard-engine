"""
EXPORT VERIFIER — Binary doğruluk, packbits, multi-head sınır, mapping doğrulama.
"""
import os, sys, struct, tempfile
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from tcad.adapters import AdapterRegistry
from tcad.domain import Document
from tcad.mapping import HookMapping


class TestBinaryVerifier:
    def _read_bin(self, path):
        with open(path, 'rb') as f:
            header = f.read(16)
            picks, hooks = struct.unpack('<II', f.read(8))
            data = f.read()
        return header, picks, hooks, data

    def test_header_integrity(self):
        plan = np.eye(8, dtype=np.uint8)
        path = os.path.join(tempfile.gettempdir(), "hdr_test.bin")
        AdapterRegistry.get('generic').export(Document(8, 8), plan, path)
        header, picks, hooks, data = self._read_bin(path)
        assert header == b'TCAD_GENERIC_V5\x00'
        assert picks == 8
        assert hooks == 8
        os.remove(path)

    def test_packbits_all_ones(self):
        """Tüm kancalar aktif — byte 0xFF olmalı."""
        plan = np.ones((1, 8), dtype=np.uint8)
        path = os.path.join(tempfile.gettempdir(), "all_ones.bin")
        AdapterRegistry.get('generic').export(Document(8, 1), plan, path)
        _, _, _, data = self._read_bin(path)
        assert data[0] == 0xFF
        os.remove(path)

    def test_packbits_all_zeros(self):
        """Hiç kanca aktif değil — byte 0x00 olmalı."""
        plan = np.zeros((1, 8), dtype=np.uint8)
        path = os.path.join(tempfile.gettempdir(), "all_zeros.bin")
        AdapterRegistry.get('generic').export(Document(8, 1), plan, path)
        _, _, _, data = self._read_bin(path)
        assert data[0] == 0x00
        os.remove(path)

    def test_packbits_alternating(self):
        """Alternatif 10101010 = 0xAA."""
        plan = np.array([[1, 0, 1, 0, 1, 0, 1, 0]], dtype=np.uint8)
        path = os.path.join(tempfile.gettempdir(), "alt.bin")
        AdapterRegistry.get('generic').export(Document(8, 1), plan, path)
        _, _, _, data = self._read_bin(path)
        assert data[0] == 0xAA
        os.remove(path)

    def test_multi_pick_byte_alignment(self):
        """10 pick, 16 hook — her pick 2 byte, toplam 20 byte data."""
        plan = np.ones((10, 16), dtype=np.uint8)
        path = os.path.join(tempfile.gettempdir(), "align.bin")
        AdapterRegistry.get('generic').export(Document(16, 10), plan, path)
        _, picks, hooks, data = self._read_bin(path)
        expected_bytes_per_pick = 16 // 8  # 2
        assert len(data) == picks * expected_bytes_per_pick
        assert all(b == 0xFF for b in data)
        os.remove(path)

    def test_non_8_aligned_hooks(self):
        """13 hook — 8'e yuvarlanmalı, padding sıfır olmalı."""
        plan = np.ones((1, 13), dtype=np.uint8)
        path = os.path.join(tempfile.gettempdir(), "non8.bin")
        AdapterRegistry.get('generic').export(Document(13, 1), plan, path)
        _, picks, hooks, data = self._read_bin(path)
        assert hooks == 13
        # 13 hooks padded to 16 = 2 bytes
        assert len(data) == 2
        # First byte: all 8 ones = 0xFF
        assert data[0] == 0xFF
        # Second byte: 5 ones then 3 zeros = 11111000 = 0xF8
        assert data[1] == 0xF8
        os.remove(path)


class TestMultiHeadSplit:
    def test_split_boundary_correctness(self):
        """HEAD1 ve HEAD2 sınır doğrulaması."""
        adapter = AdapterRegistry.get('generic')
        adapter._profile.max_hooks = 100

        # 250 hook — 3 head'e bölünmeli
        plan = np.zeros((5, 250), dtype=np.uint8)
        plan[:, 0] = 1    # HEAD1'de olmalı
        plan[:, 99] = 1   # HEAD1'de olmalı
        plan[:, 100] = 1  # HEAD2'de olmalı
        plan[:, 249] = 1  # HEAD3'te olmalı

        base = os.path.join(tempfile.gettempdir(), "split_bnd.bin")
        adapter.export(Document(250, 5), plan, base)

        for i in range(1, 4):
            p = os.path.join(tempfile.gettempdir(), f"split_bnd_HEAD{i}.bin")
            assert os.path.exists(p)
            header, picks, hooks, data = self._read_bin(p)
            assert picks == 5
            if i < 3:
                assert hooks == 100
            else:
                assert hooks == 50  # remaining
            os.remove(p)

    def _read_bin(self, path):
        with open(path, 'rb') as f:
            header = f.read(16)
            picks, hooks = struct.unpack('<II', f.read(8))
            data = f.read()
        return header, picks, hooks, data


class TestMappingExportChain:
    def test_known_activation_pattern(self):
        """Bilinen lift plan + mapping = beklenen hook aktivasyonu."""
        # 4 tel, 4 hook, düz tahar
        lp = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
        ], dtype=np.uint8)
        mapping = np.array([0, 1, 2, 3], dtype=np.int64)
        m_plan = HookMapping.apply_fast(lp, mapping, 4)

        # Pick 0: hook 0 ve 2 aktif
        assert m_plan[0, 0] == 1
        assert m_plan[0, 1] == 0
        assert m_plan[0, 2] == 1
        assert m_plan[0, 3] == 0

        # Pick 1: hook 1 ve 3 aktif
        assert m_plan[1, 0] == 0
        assert m_plan[1, 1] == 1
        assert m_plan[1, 2] == 0
        assert m_plan[1, 3] == 1

    def test_dead_hook_exclusion(self):
        """Dead hook (-1) veri yazmamalı."""
        lp = np.ones((2, 4), dtype=np.uint8)
        mapping = np.array([0, -1, 2, -1], dtype=np.int64)
        m_plan = HookMapping.apply_fast(lp, mapping, 4)
        assert m_plan[0, 0] == 1  # tel 0 → hook 0
        assert m_plan[0, 1] == 0  # tel 1 dead → hook 1 boş
        assert m_plan[0, 2] == 1  # tel 2 → hook 2
        assert m_plan[0, 3] == 0  # tel 3 dead → hook 3 boş

    def test_collision_bitwise_or(self):
        """Aynı hook'a 2 tel atandığında bitwise OR doğru çalışmalı."""
        lp = np.array([
            [1, 0],
            [0, 1],
        ], dtype=np.uint8)
        mapping = np.array([0, 0], dtype=np.int64)  # her iki tel aynı hook'a
        m_plan = HookMapping.apply_fast(lp, mapping, 2)
        # Pick 0: tel 0=1, tel 1=0 → hook 0 = 1|0 = 1
        assert m_plan[0, 0] == 1
        # Pick 1: tel 0=0, tel 1=1 → hook 0 = 0|1 = 1
        assert m_plan[1, 0] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
