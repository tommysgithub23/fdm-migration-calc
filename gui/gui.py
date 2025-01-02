from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout
from single_layer_gui import SingleLayerTab


class MainWindow(QMainWindow):
    """
    Haupt-GUI-Fenster. Dient als Container für verschiedene Modelle (Tabs).
    """
    def __init__(self):
        super().__init__()

        # Titel und Größe des Fensters festlegen
        self.setWindowTitle("Migration Calculation")
        self.setGeometry(100, 100, 1000, 600)
        
        # Zentraler Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Hauptlayout für den zentralen Container
        self.main_layout = QVBoxLayout(central_widget)

        # Tab-Widget für verschiedene Modelle
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)  # Füge das Tab-Widget unterhalb des Spacers hinzu

        # Tabs hinzufügen
        self.add_tabs()

    def add_tabs(self):
        """Fügt verschiedene Modelle als Tabs hinzu."""
        # Tab für das Single-Layer-Model
        single_layer_tab = SingleLayerTab()
        self.tab_widget.addTab(single_layer_tab, "Single-Layer Model")
        

