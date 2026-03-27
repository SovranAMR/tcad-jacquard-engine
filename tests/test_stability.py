"""
STABILITY TEST — Long-run bellek ve state tutarlılığı.
1000 compile, 1000 view switch, 500 save/load, 500 undo/redo döngüleri.
"""
import os, sys, time, tempfile, tracemalloc
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from tcad.domain import Document, PatchCommand
from tcad.weaves import WeaveLibrary, WeaveEngine
from tcad.threads import FabricSimulator
from tcad.validation import ValidationEngine
from tcad.fileio import save_project, load_project


class TestCompileStability:
    def test_1000_compile_cycles(self):
        """1000 compile döngüsünde memory leak ve state bozulması."""
        doc = Document(100, 100)
        doc.grid[20:40, 20:40] = 1
        doc.color_weaves[1] = WeaveLibrary.plain()

        tracemalloc.start()
        snap_start = tracemalloc.take_snapshot()

        for i in range(1000):
            doc.weave_phases = {"c_1": (i % 5, i % 3)}
            doc.lift_plan = WeaveEngine.build_lift_plan(
                doc.grid, doc.region_mask,
                doc.color_weaves, doc.region_weaves,
                doc.weave_phases)

        snap_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Grid bozulmamalı
        assert doc.grid[25, 25] == 1
        assert doc.grid[0, 0] == 0
        assert doc.lift_plan.shape == (100, 100)

        # Memory: snapshot farkına bak
        stats = snap_end.compare_to(snap_start, 'lineno')
        total_increase = sum(s.size_diff for s in stats if s.size_diff > 0)
        print(f"\n  [1000 compile] memory increase: {total_increase / 1024:.1f} KB")
        # 10MB'dan fazla artış = şüpheli
        assert total_increase < 10 * 1024 * 1024, \
            f"Memory leak şüphesi: {total_increase / 1e6:.1f} MB artış"


class TestViewSwitchStability:
    def test_1000_view_switches(self):
        """1000 view mode geçişinde state corruption."""
        doc = Document(100, 100)
        doc.grid[10:30, 10:30] = 1
        doc.color_weaves[1] = WeaveLibrary.satin(5, 2)
        original_grid = doc.grid.copy()

        doc.lift_plan = WeaveEngine.build_lift_plan(
            doc.grid, doc.region_mask,
            doc.color_weaves, doc.region_weaves, {})
        doc.fabric_rgb = FabricSimulator.render_fabric(
            doc.lift_plan, doc.warp_seq, doc.weft_seq)

        modes = ['design', 'weave', 'fabric']
        for i in range(1000):
            doc.view_mode = modes[i % 3]

        doc.view_mode = 'design'
        assert np.array_equal(doc.grid, original_grid), \
            "1000 view switch sonrası grid bozuldu"
        assert doc.lift_plan is not None
        assert doc.fabric_rgb is not None


class TestSaveLoadStability:
    def test_500_save_load_cycles(self):
        """500 save/load döngüsünde veri bozulması."""
        doc = Document(80, 80)
        doc.grid[10:30, 10:30] = 3
        doc.palette[3] = (42, 84, 126)
        doc.region_mask[5:15, 5:15] = 2
        path = os.path.join(tempfile.gettempdir(), "stability_test.tcad")

        for i in range(500):
            save_project(doc, path)
            load_project(doc, path)

        assert doc.width == 80
        assert doc.height == 80
        assert doc.grid[15, 15] == 3
        assert doc.palette[3] == (42, 84, 126)
        assert doc.region_mask[10, 10] == 2
        os.remove(path)
        print(f"\n  [500 save/load] veri bütünlüğü korundu")


class TestUndoRedoStability:
    def test_500_undo_redo_cycles(self):
        """500 undo/redo döngüsünde bellek ve tutarlılık."""
        doc = Document(50, 50)
        commands = []
        for i in range(500):
            x, y = i % 40, i % 40
            old_p = doc.grid[y:y+5, x:x+5].copy()
            new_p = np.full((5, 5), (i % 254) + 1, dtype=np.uint8)
            doc.grid[y:y+5, x:x+5] = new_p
            cmd = PatchCommand(doc, x, y, old_p, new_p, lambda *a: None)
            commands.append(cmd)

        # Undo all
        for cmd in reversed(commands):
            cmd.undo()
        assert np.all(doc.grid == 0), "500 undo sonrası grid sıfır olmalı"

        # Redo all
        for cmd in commands:
            cmd.redo()
        last = 499
        x, y = last % 40, last % 40
        assert doc.grid[y, x] == (last % 254) + 1

        # Undo half, redo half
        for cmd in reversed(commands[250:]):
            cmd.undo()
        for cmd in commands[250:]:
            cmd.redo()
        assert doc.grid[y, x] == (last % 254) + 1
        print(f"\n  [500 undo/redo] state tutarlı")


class TestFabricRenderStability:
    def test_repeated_fabric_render(self):
        """500 ardışık fabric render — bellek şişmesi kontrolü."""
        doc = Document(200, 200)
        doc.grid[50:100, 50:100] = 1
        doc.color_weaves[1] = WeaveLibrary.twill(2, 1)
        doc.lift_plan = WeaveEngine.build_lift_plan(
            doc.grid, doc.region_mask,
            doc.color_weaves, doc.region_weaves, {})

        tracemalloc.start()
        snap_start = tracemalloc.take_snapshot()

        for _ in range(500):
            doc.fabric_rgb = FabricSimulator.render_fabric(
                doc.lift_plan, doc.warp_seq, doc.weft_seq)

        snap_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        assert doc.fabric_rgb.shape == (200, 200, 4)
        stats = snap_end.compare_to(snap_start, 'lineno')
        total_increase = sum(s.size_diff for s in stats if s.size_diff > 0)
        print(f"\n  [500 fabric render] memory increase: {total_increase / 1024:.1f} KB")
        assert total_increase < 20 * 1024 * 1024


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
