from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QFormLayout, QLineEdit,
    QLabel, QCheckBox, QComboBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from sl_model_functions import migrationsmodell_piringer, calculate_max_cp0, plot_results_area
import os
import numpy as np
from datetime import datetime


class SingleLayerTab(QWidget):
    """
    GUI für das Single-Layer-Model. Organisiert in Tabs für Eingabe und Berechnung.
    """
    def __init__(self):
        super().__init__()

        # Hauptlayout erstellen
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Sub-Tab-Widget für Eingabe und Berechnung
        self.sl_sub_tab_widget = QTabWidget()

        # Tabs hinzufügen
        self.create_input_tab()
        self.create_calculation_tab()

        # Sub-Tab-Widget zum Hauptlayout hinzufügen
        self.main_layout.addWidget(self.sl_sub_tab_widget)

    def create_input_tab(self):
        """Erstellt den Eingabe-Tab mit physikalisch/chemischen und geometrischen Eingaben."""
        sl_input_tab = QWidget()
        sl_input_tab_layout = QHBoxLayout(sl_input_tab)

        # Physikalisch-chemische und geometrische Eingaben sowie grafische Darstellung
        sl_phy_chem_layout = self.create_phy_chem_inputs()
        sl_geo_layout = self.create_geo_inputs()
        sl_graphical_layout = self.create_grafical_setup()

        # Rechte Spalte für Geometrie und Grafik
        sl_input_tab_right_layout = QVBoxLayout()
        sl_input_tab_right_layout.addLayout(sl_geo_layout)
        sl_input_tab_right_layout.addLayout(sl_graphical_layout)

        # Hinzufügen der Layouts
        sl_input_tab_layout.addLayout(sl_phy_chem_layout, 1)
        sl_input_tab_layout.addLayout(sl_input_tab_right_layout, 2)

        # Tab hinzufügen
        self.sl_sub_tab_widget.addTab(sl_input_tab, "Eingabe")

    def create_calculation_tab(self):
        """Erstellt den Berechnungs-Tab mit Platzhaltern für Ergebnisse."""
        calculation_tab = QWidget()
        calculation_tab_layout = QVBoxLayout(calculation_tab)

        # Platzhalter für Berechnungsergebnisse
        calculation_tab_layout.addWidget(QLabel("Hier kommen die Berechnungsergebnisse hin."))

        # Tab hinzufügen
        self.sl_sub_tab_widget.addTab(calculation_tab, "Berechnung")

    def create_phy_chem_inputs(self):
        # Create layout for physical/chemical inputs
        form_layout = QFormLayout()

        # Create a QLabel for the headline
        headline_label = QLabel("<b>Physikalische/chemische Größen</b>")
        headline_label.setAlignment(Qt.AlignLeft)  # Align left like the form layout rows
        headline_label.setContentsMargins(0, 0, 0, 0)  # Remove any additional margins
        form_layout.addRow(headline_label)  # Add headline directly to the form layout

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

        # Narrow input fields
        for input_field in [T_C_input, t_max_input, M_r_input, c_P0_input, P_density_input, F_density_input, D_P_known_input, K_PF_input, dt_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower
        
        # First row of the form
        form_layout.addRow(self._create_labeled_row("Material", "", material_dropdown))
        # Other rows of the form
        form_layout.addRow(self._create_labeled_row("T<sub>C</sub>", "°C", T_C_input))
        form_layout.addRow(self._create_labeled_row("t<sub>max</sub>", "s", t_max_input))
        form_layout.addRow(self._create_labeled_row("Δt", "s", dt_input))
        form_layout.addRow(self._create_labeled_row("M<sub>r</sub>", "g/mol", M_r_input))
        form_layout.addRow(self._create_labeled_row("c<sub>P0</sub>", "mg/kg", c_P0_input))
        form_layout.addRow(self._create_labeled_row("ρ<sub>P</sub>", "g/cm³", P_density_input))
        form_layout.addRow(self._create_labeled_row("ρ<sub>F</sub>", "g/cm³", F_density_input))
        form_layout.addRow(self._create_labeled_row("K<sub>PF</sub>", "-", K_PF_input))
        
        
        # Zeile für die Eingabe des Diffusionskoeffizienten mir "Checkbox toggle"
        D_P_known_input.setEnabled(False)  # Default: disabled
        
        def toggle_d_p_input(checked):
            D_P_known_input.setEnabled(checked)
        
        # Signal verbinden
        D_P_checkbox.toggled.connect(toggle_d_p_input)
        
        # Add checkbox and input field for diffusion coefficient
        D_P_row = self._create_labeled_row("D<sub>P</sub>", "cm²/s", D_P_known_input)
        D_P_row.layout().insertWidget(3, D_P_checkbox)  # Add the checkbox in the row
        form_layout.addRow(D_P_row)

        # Tighten vertical spacing
        form_layout.setVerticalSpacing(4)  # Minimal spacing for better alignment
        form_layout.setContentsMargins(0, 0, 0, 0)  # Reduce overall margins

        # Create a main layout to return
        phy_chem_layout = QVBoxLayout()
        phy_chem_layout.addLayout(form_layout)

        return phy_chem_layout

    def create_geo_inputs(self):
        # Create layout for geometric inputs
        geo_layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Create a QLabel for the headline
        headline_label = QLabel("<b>Geometrische Größen</b>")
        headline_label.setAlignment(Qt.AlignLeft)  # Align left like in form layout
        headline_label.setContentsMargins(0, 0, 0, 0)  # Adjust margins to match the form layout
        geo_layout.addWidget(headline_label)
        
        # Add input fields
        d_P_input = QLineEdit()
        d_F_input = QLineEdit()
        V_P_input = QLineEdit()
        V_F_input = QLineEdit()
        A_PF_input = QLineEdit()
        sim_case_dropdown = QComboBox()
        simulation_case = ["worst","best"]
        sim_case_dropdown.addItems(simulation_case)
        sim_case_dropdown.setMaximumWidth(85)

        # Narrow input fields
        for input_field in [d_P_input, d_F_input, V_P_input, V_F_input, A_PF_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower

        # Create rows for combined inputs
        row_1_layout = QHBoxLayout()
        row_1_layout.addWidget(self._create_labeled_row("d<sub>P</sub>", "cm", d_P_input))
        row_1_layout.addWidget(self._create_labeled_row("d<sub>F</sub>", "cm", d_F_input))

        row_2_layout = QHBoxLayout()
        row_2_layout.addWidget(self._create_labeled_row("V<sub>P</sub>", "cm³", V_P_input))
        row_2_layout.addWidget(self._create_labeled_row("V<sub>F</sub>", "cm³", V_F_input))

        row_3_layout = QHBoxLayout()
        row_3_layout.addWidget(self._create_labeled_row("A<sub>PF</sub>", "dm²", A_PF_input))
        row_3_layout.addWidget(self._create_labeled_row("Simulation Case", "", sim_case_dropdown))

        # Add rows to the form layout
        form_layout.addRow(row_1_layout)
        form_layout.addRow(row_2_layout)
        form_layout.addRow(row_3_layout)

        # Adjust spacing between rows
        form_layout.setVerticalSpacing(3)  # Adjust spacing between rows

        # Add form layout to the main layout
        geo_layout.addLayout(form_layout)

        return geo_layout

    def create_grafical_setup(self):
        """Erstellt den Bereich für die grafische Darstellung."""
        layout = QVBoxLayout()

        # Überschrift
        headline_label = QLabel("<b>Grafische Darstellung der Schichten</b>")
        headline_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(headline_label)

        # Grafikbereich
        graphics_view = QGraphicsView()
        graphics_scene = QGraphicsScene()
        graphics_view.setScene(graphics_scene)

        # Beispielhafte Rechtecke für Schichten
        rect_f = QGraphicsRectItem(0, 0, 200, 200)
        rect_f.setBrush(Qt.blue)
        graphics_scene.addItem(rect_f)

        rect_p = QGraphicsRectItem(-10, 0, 10, 200)
        rect_p.setBrush(Qt.red)
        graphics_scene.addItem(rect_p)

        # Grafikbereich hinzufügen
        layout.addWidget(graphics_view)
        
        # Button hinzufügen
        start_button = QPushButton("Berechnung starten")
        start_button.setFixedSize(150, 30)  # Button-Größe anpassen
        start_button.clicked.connect(self.start_calculation)  # Signal verbinden
        layout.addWidget(start_button)
        layout.setAlignment(start_button, Qt.AlignRight)
        
        return layout
    
    # Hier weitermachen, Ich muss die Inputs als Instanzvariable definieren, damit ich von anderen funktionen darauf zugreifen kann. Momentan sind die nur lokal definiert. 
#     also so: 
#         # Add input fields
# self.T_C_input = QLineEdit()
# self.t_max_input = QLineEdit()
# self.M_r_input = QLineEdit()
# self.c_P0_input = QLineEdit()
# self.P_density_input = QLineEdit()
# self.F_density_input = QLineEdit()
# self.D_P_known_input = QLineEdit()
# self.K_PF_input = QLineEdit()
# self.dt_input = QLineEdit()
    def start_calculation(self):
        print("Berechnung gestartet!")
        """Führt die Berechnung basierend auf den Eingaben durch."""
        # Physikalisch-chemische Eigenschaften
        M_r = float(self.M_r_input.text())
        T_C = float(self.T_C_input.text())
        c_P0 = float(self.c_P0_input.text())
        Material = self.material_dropdown.currentText()
        P_density = float(self.P_density_input.text())
        F_density = float(self.F_density_input.text())
        D_P_known = None if not self.D_P_known_input.text() else float(self.D_P_known_input.text())
        K_PF = float(self.K_PF_input.text())
        t_max = float(self.t_max_input.text())

        # Geometrische Größen
        d_P = float(self.d_P_input.text())
        d_F = float(self.d_F_input.text())
        V_P = float(self.V_P_input.text())  
        V_F = float(self.V_F_input.text())
        A_PF = float(self.A_PF_input.text())
        
        # Case
        simulation_case = self.sim_case_dropdown.currentText()

        # Modellparameter nach Piringer
        dt = float(self.dt_input.text())

        # Berechnung der spez. Migrationsmenge
        results_area = migrationsmodell_piringer(M_r, T_C, c_P0, Material, P_density, F_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_known, simulation_case)

        # Ergebnisse in der Berechnungstabelle plotten
        self.calculation_tab_layout.addWidget(QLabel("Ergebnisse der Berechnung:"))
        for i, result in enumerate(results_area):
            self.calculation_tab_layout.addWidget(QLabel(f"Zeitschritt {i}: {result}"))

    def _create_labeled_row(self, label_text, unit_text, input_field):
            # Create a horizontal layout for the row
            row_layout = QHBoxLayout()

            # Create the label with LaTeX-like text
            label = QLabel(f"<html>{label_text}</html>")
            label.setMinimumWidth(40)  # Optional: Adjust width for consistent alignment

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

