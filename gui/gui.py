from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt
from single_layer_gui import SingleLayerSuiteTab
from multi_layer_gui import MultiLayerSuiteTab
from curve_fitting_gui import CurveFittingTab
import os

class MainWindow(QMainWindow):
    """
    Haupt-GUI-Fenster. Dient als Container für verschiedene Modelle (Tabs).
    """
    def __init__(self):
        super().__init__()

        # 1) Fenster-Icon setzen (relativ zum Skript-Pfad)
        base = os.path.dirname(__file__)
        logo_path = os.path.join(base, "IKK_logo.svg")
        self.setWindowIcon(QIcon(logo_path))

        # 2) Titel und Größe des Fensters festlegen
        self.setWindowTitle("Migrationsmodellierung")
        self.setGeometry(100, 100, 1000, 600)

        # 3) Zentralen Container + Layout anlegen
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # Einheitlicher Button-Style für markierte Buttons (nicht global, damit einzelne Buttons nativ bleiben können)
        self.setStyleSheet(
            """
            QPushButton[appStyle="true"] {
                background-color: #2c2c2c;
                color: white;
                border: 1px solid #F06D1D;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton[appStyle="true"]:hover { background-color: #333333; }
            QPushButton[appStyle="true"]:pressed { background-color: #242424; }
            QPushButton[appStyle="true"]:disabled {
                background-color: #d6d6d6;
                color: #7a7a7a;
                border-color: #F06D1D;
            }
            QToolButton {
                background-color: #2c2c2c;
                color: white;
                border: 1px solid #F06D1D;
                border-radius: 4px;
                padding: 2px;
            }
            QToolButton:hover { background-color: #333333; }
            QToolButton:pressed { background-color: #242424; }
            """
        )

        # 4) Logo-Label erstellen und ins Layout packen
        logo_label = QLabel()
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            print("Logo nicht gefunden unter:", logo_path)
        else:
            pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignRight)
        self.main_layout.addWidget(logo_label)

        # 5) Tab-Widget für Single- und Multi-Layer-GUI
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # 6) Tabs hinzufügen
        self.add_tabs()


    def add_tabs(self):
        # Tab für das Single-Layer-Model
        single_layer_tab = SingleLayerSuiteTab()
        self.tab_widget.addTab(single_layer_tab, "Single-Layer Modell")

        # Tab für das Multi-Layer-Model
        multi_layer_tab = MultiLayerSuiteTab()
        self.tab_widget.addTab(multi_layer_tab, "Multi-Layer Modell")

        # Curve Fitting ist jetzt im Single-Layer-Bereich enthalten
