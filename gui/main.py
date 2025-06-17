import os
import sys
from PySide6 import __file__ as pyside6_path
from PySide6.QtWidgets import QApplication
from gui import MainWindow

plugin_path = os.path.join(os.path.dirname(pyside6_path), "Qt", "plugins")
if os.path.exists(plugin_path):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())