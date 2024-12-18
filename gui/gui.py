from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QMenu, 
                               QComboBox, QTableWidget, QTableWidgetItem, QPushButton, QSplitter, QLabel)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Migration Calculation")
        self.setGeometry(100, 100, 800, 600)

        self.layers = []  # Initially no layers

        self._setup_ui()

    def _setup_ui(self):
        # Create Menu Bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Datei")

        new_calc_action = QAction("New Calculation", self)
        new_calc_action.triggered.connect(self.new_calculation)
        file_menu.addAction(new_calc_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        # Initially empty layout until "New Calculation" is selected
        self.setup_widget = None
        self.graph_widget = None

    def new_calculation(self):
        # Clear existing widgets if any
        if self.setup_widget:
            self.main_layout.removeWidget(self.setup_widget)
            self.setup_widget.deleteLater()
        if self.graph_widget:
            self.main_layout.removeWidget(self.graph_widget)
            self.graph_widget.deleteLater()

        # Create new layout after "New Calculation"
        self.setup_widget = QWidget()
        setup_layout = QHBoxLayout()
        self.setup_widget.setLayout(setup_layout)

        model_layout = QVBoxLayout()
        model_lable = QLabel("Model")
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(["Multi-Layer Model", "Single-Layer Model"])
        self.model_dropdown.setFixedWidth(200)
        self.model_dropdown.currentIndexChanged.connect(self.update_model)
        setup_layout.addWidget(self.model_dropdown)

        model_layout.addWidget(model_lable)
        # model_layout.addLayout

        self.layer_table = QTableWidget()
        self.layer_table.setColumnCount(5)
        self.layer_table.setHorizontalHeaderLabels(["Material", "Dicke (cm)", "nx", "C_init", "D (cm²/s)"])
        self.layer_table.setFixedHeight(200)  # Adjusted height for ~5 rows
        setup_layout.addWidget(self.layer_table)

        self.main_layout.addWidget(self.setup_widget)
        
        # Create horizontal button layout and buttons
        button_layout = QHBoxLayout()
        self.add_layer_button = QPushButton("Add Layer")
        self.add_layer_button.clicked.connect(self.add_layer)
        self.add_layer_button.setEnabled(False)  # Initially disabled
        self.add_layer_button.setFixedWidth(150)
        self.add_layer_button.setFixedHeight(30)
        button_layout.addWidget(self.add_layer_button)

        self.remove_layer_button = QPushButton("Remove Layer")
        self.remove_layer_button.clicked.connect(self.remove_layer)
        self.remove_layer_button.setEnabled(False)  # Initially disabled
        self.remove_layer_button.setFixedWidth(150)
        self.remove_layer_button.setFixedHeight(30)
        button_layout.addWidget(self.remove_layer_button)
        
        # Add the button layout to the main layout 
        setup_layout.addLayout(button_layout)
        # Create graphical representation
        self.graph_widget = QWidget()
        graph_layout = QVBoxLayout()
        self.graph_widget.setLayout(graph_layout)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(400, 300)  # Smaller graph size
        graph_layout.addWidget(self.canvas)

        self.main_layout.addWidget(self.graph_widget, alignment=Qt.AlignLeft | Qt.AlignBottom)

        self.update_model()

    def update_model(self):
        selected_model = self.model_dropdown.currentText()
        if selected_model == "Multi-Layer Model":
            self.layers = [
                {"material": "Layer 1", "d": 0.2, "nx": 10, "C_init": 220, "D": 1e-6},
                {"material": "Kontaktphase", "d": 1.85, "nx": 50, "C_init": 0, "D": None}
            ]
            self.add_layer_button.setEnabled(True)
            self.remove_layer_button.setEnabled(True)
        elif selected_model == "Single-Layer Model":
            self.layers = [
                {"material": "Polymerschicht", "d": 0.2, "nx": 10, "C_init": 220, "D": 1e-6},
                {"material": "Kontaktphase", "d": 1.85, "nx": 50, "C_init": 0, "D": None}
            ]
            self.add_layer_button.setEnabled(False)
            self.remove_layer_button.setEnabled(False)

        self.update_layer_table()
        self.update_layer_graph()

    def update_layer_table(self):
        self.layer_table.setRowCount(len(self.layers))
        for row, layer in enumerate(self.layers):
            self.layer_table.setItem(row, 0, QTableWidgetItem(layer["material"]))
            self.layer_table.setItem(row, 1, QTableWidgetItem(str(layer["d"])))
            self.layer_table.setItem(row, 2, QTableWidgetItem(str(layer["nx"])))
            self.layer_table.setItem(row, 3, QTableWidgetItem(str(layer["C_init"])))
            self.layer_table.setItem(row, 4, QTableWidgetItem(str(layer["D"] if layer["D"] is not None else "-")))

    def add_layer(self):
        if self.model_dropdown.currentText() == "Multi-Layer Model":
            new_layer = {"material": f"Layer {len(self.layers) + 1}", "d": 0.1, "nx": 5, "C_init": 0, "D": 1e-6}
            self.layers.insert(-1, new_layer)
            self.update_layer_table()
            self.update_layer_graph()

    def remove_layer(self):
        if self.model_dropdown.currentText() == "Multi-Layer Model" and len(self.layers) > 2:
            self.layers.pop()
            self.update_layer_table()
            self.update_layer_graph()

    def update_layer_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Data for plotting
        thicknesses = [layer["d"] for layer in self.layers]
        materials = [layer["material"] for layer in self.layers]
        y_positions = range(len(thicknesses))

        # Create horizontal bar chart
        ax.barh(y_positions, thicknesses, align='center')
        ax.set_yticks(y_positions)
        ax.set_yticklabels(materials)
        ax.set_xlabel("Thickness (cm)")
        ax.set_title("Layer Structure")

        self.canvas.draw()

# Example usage
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
