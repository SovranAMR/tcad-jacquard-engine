import sys
import os

# Yüksek çözünürlüklü ekran (DPI) optimizasyonu
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtWidgets import QApplication
from tcad.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Jacquard CAD Professional")
    app.setStyle("Fusion")

    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
