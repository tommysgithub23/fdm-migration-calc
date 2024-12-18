from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
                               QTableWidget, QTableWidgetItem, QHBoxLayout, QFormLayout, QLineEdit, QLabel, QCheckBox, QComboBox, QGraphicsView,QGraphicsScene, QGraphicsRectItem)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Migration Calculation")
        self.setGeometry(100, 100, 800, 600)
        self._setup_ui()

    def _setup_ui(self):
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_sl_tab(), "Single-Layer Model")
        main_layout.addWidget(self.tab_widget)

    def create_sl_tab(self):
        # Tab for Single-Layer Model
        sl_tab = QWidget()
        
        # Main layout for the Single-Layer-Model-Tab
        sl_main_layout = QVBoxLayout()
        
        sl_sub_tab_widget = QTabWidget()
        
        # "Eingabe" - Tab
        sl_input_tab = QWidget() 
        
        # Horizontal layout for the input tab
        sl_input_tab_layout = QHBoxLayout()
        
        # Creating the layout and inputs for physical/chemical and geometric paramters
        sl_phy_chem_layout = self.create_phy_chem_inputs()
        sl_geo_layout = self.create_geo_inputs()
        sl_grafical_setup_layout = self.create_grafical_setup()
        
        # Add vertical layouts to the horzontal layout
        sl_input_tab_layout.addLayout(sl_phy_chem_layout)
        sl_input_tab_layout.addLayout(sl_geo_layout)
        sl_input_tab_layout.addLayout(sl_grafical_setup_layout)
        
        sl_input_tab.setLayout(sl_input_tab_layout)

        # "Berechnung" Tab
        calculation_tab = QWidget()
        calculation_tab_layout = QVBoxLayout()
        
        # Example placeholder: Add a QLabel for now
        calculation_tab_layout.addWidget(QLabel("Hier kommen die Berechnungsergebnisse hin."))
        calculation_tab.setLayout(calculation_tab_layout)
        
        # Add sub-tabs to the sub-tab widget
        sl_sub_tab_widget.addTab(sl_input_tab, "Eingabe")
        sl_sub_tab_widget.addTab(calculation_tab, "Berechnung")
        
        # Add the sub-tab widget to the main layout
        sl_main_layout.addWidget(sl_sub_tab_widget)
        
        # Set the main layout for the Single-Layer Model Tab
        sl_tab.setLayout(sl_main_layout)
        
        return sl_tab
    
    def create_phy_chem_inputs(self):
        # Create layout for physical/chemical inputs
        phy_chem_layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("<b>Physikalische/chemische Größen<b>"), QWidget())
        
        # Add input fields
        T_C_input = QLineEdit()
        t_max_input = QLineEdit()
        M_r_input = QLineEdit()
        c_P0_input = QLineEdit()
        P_density_input = QLineEdit()
        F_density_input = QLineEdit()
        D_P_known_input = QLineEdit()
        D_P_checkbox = QCheckBox("Bekannt")  # Checkbox to toggle D_P_known_input
        K_PF_input = QLineEdit()
        dt_input = QLineEdit()

        # Material dropdown
        material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]
        material_dropdown = QComboBox()
        material_dropdown.addItems(material_list)

        # Configure checkbox behavior
        D_P_known_input.setEnabled(False)  # Default: disabled
        D_P_checkbox.stateChanged.connect(lambda state: D_P_known_input.setEnabled(state == Qt.Checked))

        # Narrow input fields
        for input_field in [T_C_input, t_max_input, M_r_input, c_P0_input, P_density_input, F_density_input, D_P_known_input, K_PF_input, dt_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower

        # First row of the form
        form_layout.addRow(self._create_labeled_row("Material", "", material_dropdown))
        # Other rows of the form
        form_layout.addRow(self._create_labeled_row("T<sub>C</sub>", "°C", T_C_input))
        form_layout.addRow(self._create_labeled_row("t<sub>max</sub>", "s", t_max_input))
        form_layout.addRow(self._create_labeled_row("M<sub>r</sub>", "g/mol", M_r_input))
        form_layout.addRow(self._create_labeled_row("c<sub>P0</sub>", "mg/kg", c_P0_input))
        form_layout.addRow(self._create_labeled_row("ρ<sub>P</sub>", "g/cm³", P_density_input))
        form_layout.addRow(self._create_labeled_row("ρ<sub>F</sub>", "g/cm³", F_density_input))
        form_layout.addRow(self._create_labeled_row("Δt", "s", dt_input))
        
        # Add checkbox and input field for diffusion coefficient
        D_P_row = self._create_labeled_row("D<sub>P</sub>", "cm²/s", D_P_known_input)
        D_P_row.layout().insertWidget(3, D_P_checkbox)  # Add the checkbox in the row
        form_layout.addRow(D_P_row)
        
        # Tighten vertical spacing
        form_layout.setVerticalSpacing(2)  # Minimal spacing
        form_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        
        phy_chem_layout.addLayout(form_layout)
        
        return phy_chem_layout
        
    def create_geo_inputs(self):
        # Create layout for geometric inputs
        geo_layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("<b>Geometrische Größen<b>"), QWidget())

        # Add input fields
        d_P_input = QLineEdit()
        d_F_input = QLineEdit()
        V_P_input = QLineEdit()
        V_F_input = QLineEdit()
        A_PF_input = QLineEdit()
        
        # Narrow input fields
        for input_field in [d_P_input, d_F_input, V_P_input, V_F_input, A_PF_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower

        # Add rows with labels, input fields, and units
        form_layout.addRow(self._create_labeled_row("d<sub>P</sub>", "cm", d_P_input))
        form_layout.addRow(self._create_labeled_row("d<sub>F</sub>", "cm", d_F_input))
        form_layout.addRow(self._create_labeled_row("V<sub>P</sub>", "cm³", V_P_input))
        form_layout.addRow(self._create_labeled_row("V<sub>F</sub>", "cm³", V_F_input))
        form_layout.addRow(self._create_labeled_row("A<sub>PF</sub>", "dm²", A_PF_input))

        # Adjust spacing between rows
        form_layout.setVerticalSpacing(3)  # Adjust spacing between rows

        # Add form layout to the main layout
        geo_layout.addLayout(form_layout)
        

        return geo_layout
        
    def _create_labeled_row(self, label_text, unit_text, input_field):
        # Create a horizontal layout for the row
        row_layout = QHBoxLayout()

        # Create the label with LaTeX-like text
        label = QLabel(f"<html>{label_text}</html>")
        label.setMinimumWidth(60)  # Optional: Adjust width for consistent alignment

        # Create the unit label
        unit_label = QLabel(unit_text)

        # Add widgets to the horizontal layout
        row_layout.addWidget(label)
        row_layout.addWidget(input_field)
        row_layout.addWidget(unit_label)

        # Stretch for spacing (optional)
        row_layout.addStretch()

        # Return the layout as a QWidget for the form layout
        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        return row_widget
    
    def create_grafical_setup(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Grafische Darstellung der Schichten</b>"))

        # Create QGraphicsView and QGraphicsScene
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setFixedHeight(300)  # Adjust the height as needed

        # Add initial rectangles to the scene
        self.d_f_rect = QGraphicsRectItem(0, 0, 100, 50)  # Example initial size for d_f
        self.d_f_rect.setBrush(Qt.blue)  # Set color for d_f layer
        self.graphics_scene.addItem(self.d_f_rect)

        self.d_p_rect = QGraphicsRectItem(0, 50, 100, 100)  # Example initial size for d_p
        self.d_p_rect.setBrush(Qt.red)  # Set color for d_p layer
        self.graphics_scene.addItem(self.d_p_rect)

        layout.addWidget(self.graphics_view)
        return layout

        
    
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
