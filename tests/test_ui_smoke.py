"""
UI SMOKE TEST — pytest-qt ile gerçek widget oluşturma ve state kontrolü.
Headless (offscreen) ortamda çalışır.
"""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication

# Ensure single QApplication
app = QApplication.instance()
if app is None:
    app = QApplication([])

from tcad.main_window import MainWindow


@pytest.fixture
def main_win():
    win = MainWindow()
    win.show()
    yield win
    win.close()


class TestWindowCreation:
    def test_window_opens(self, main_win):
        assert main_win.isVisible()
        assert main_win.windowTitle().startswith("Jacquard")

    def test_panels_exist(self, main_win):
        assert main_win.pal_panel is not None
        assert main_win.prop_panel is not None
        assert main_win.cam_panel is not None
        assert main_win.thread_panel is not None

    def test_canvas_exists(self, main_win):
        assert main_win.canvas is not None
        assert main_win.canvas.qimage is not None

    def test_initial_state(self, main_win):
        assert main_win.active_tool == 'pencil'
        assert main_win.active_color == 1
        assert main_win.doc.view_mode == 'design'


class TestToolSwitching:
    def test_set_tool(self, main_win):
        for tool in ('pencil', 'eraser', 'fill', 'line', 'rect', 'select'):
            main_win.set_tool(tool)
            assert main_win.active_tool == tool


class TestViewToggle:
    def test_toggle_without_compile(self, main_win):
        """Compile edilmeden toggle — weave'e geçmemeli."""
        main_win._toggle_view()
        assert main_win.doc.view_mode == 'design'

    def test_toggle_with_compile(self, main_win):
        """Compile sonrası toggle — design→weave."""
        main_win.doc.grid[5:15, 5:15] = 1
        main_win.cam_panel.compile_plan()
        assert main_win.doc.view_mode == 'weave'
        assert main_win.doc.lift_plan is not None

        # weave→design (fabric_rgb yok)
        main_win._toggle_view()
        assert main_win.doc.view_mode == 'design'


class TestCompileButton:
    def test_compile_changes_state(self, main_win):
        main_win.doc.grid[5:15, 5:15] = 1
        main_win.doc.color_weaves[1] = None  # No weave
        main_win.cam_panel.compile_plan()
        assert main_win.doc.lift_plan is not None
        assert main_win.doc.view_mode == 'weave'


class TestNewProject:
    def test_new_clears_state(self, main_win):
        main_win.doc.grid[0:10, 0:10] = 5
        main_win.doc.is_dirty = False  # Skip save dialog
        main_win.cmd_new()
        assert main_win.doc.width == 200
        assert main_win.doc.height == 200
        assert np.all(main_win.doc.grid == 0)


class TestCanvasRebuild:
    def test_rebuild_design_mode(self, main_win):
        main_win.doc.view_mode = 'design'
        main_win.canvas.rebuild_qimage()
        assert main_win.canvas.qimage is not None
        assert main_win.canvas.qimage.format().value >= 0

    def test_rebuild_weave_mode(self, main_win):
        main_win.doc.grid[5:15, 5:15] = 1
        main_win.cam_panel.compile_plan()
        main_win.canvas.rebuild_qimage()
        assert main_win.canvas.qimage is not None

    def test_palette_update(self, main_win):
        main_win.doc.palette[1] = (255, 0, 0)
        main_win.canvas.update_palette()
        # No crash = pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
