from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QFormLayout, QLineEdit,
    QLabel, QCheckBox, QComboBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
    QPushButton, QSpacerItem, QSizePolicy, QFileDialog
)
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
from sl_model_functions import migrationsmodell_piringer, calculate_max_cp0, plot_results_area
import numpy as np
import os
import csv


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
        """Erstellt den Berechnungs-Tab mit Ergebnissen."""
        self.calculation_tab = QWidget()
        calculation_tab_layout = QVBoxLayout(self.calculation_tab)

        # Matplotlib Canvas für Plots
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        calculation_tab_layout.addWidget(self.canvas)

        # Tab hinzufügen
        self.sl_sub_tab_widget.addTab(self.calculation_tab, "Berechnung")
        
        # Export Button
        self.add_export_button()

    def create_phy_chem_inputs(self):
        # Create layout for physical/chemical inputs
        form_layout = QFormLayout()

        # Create a QLabel for the headline
        headline_label = QLabel("<b>Physikalische/chemische Größen</b>")
        headline_label.setAlignment(Qt.AlignLeft)  # Align left like the form layout rows
        headline_label.setContentsMargins(0, 0, 0, 0)  # Remove any additional margins
        form_layout.addRow(headline_label)  # Add headline directly to the form layout

        # Add input fields
        self.T_C_input = QLineEdit()
        self.t_max_input = QLineEdit()
        self.M_r_input = QLineEdit()
        self.c_P0_input = QLineEdit()
        self.P_density_input = QLineEdit()
        self.F_density_input = QLineEdit()
        self.D_P_known_input = QLineEdit()
        self.D_P_checkbox = QCheckBox("Bekannt")  # Checkbox to toggle D_P_known_input
        self.K_PF_input = QLineEdit()
        self.dt_input = QLineEdit()

        # Material dropdown
        material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]
        self.material_dropdown = QComboBox()
        self.material_dropdown.addItems(material_list)      

        # Narrow input fields
        for input_field in [self.T_C_input, self.t_max_input, self.M_r_input, self.c_P0_input, 
                            self.P_density_input, self.F_density_input, self.D_P_known_input, self.K_PF_input, self.dt_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower
        
        # First row of the form
        form_layout.addRow(self._create_labeled_row("Material", "", self.material_dropdown))
        # Other rows of the form
        form_layout.addRow(self._create_labeled_row("T<sub>C</sub>", "°C", self.T_C_input))
        form_layout.addRow(self._create_labeled_row("t<sub>max</sub>", "s", self.t_max_input))
        form_layout.addRow(self._create_labeled_row("Δt", "s", self.dt_input))
        form_layout.addRow(self._create_labeled_row("M<sub>r</sub>", "g/mol", self.M_r_input))
        form_layout.addRow(self._create_labeled_row("c<sub>P0</sub>", "mg/kg", self.c_P0_input))
        form_layout.addRow(self._create_labeled_row("ρ<sub>P</sub>", "g/cm³", self.P_density_input))
        form_layout.addRow(self._create_labeled_row("ρ<sub>F</sub>", "g/cm³", self.F_density_input))
        form_layout.addRow(self._create_labeled_row("K<sub>PF</sub>", "-", self.K_PF_input))
        
        
        # Zeile für die Eingabe des Diffusionskoeffizienten mir "Checkbox toggle"
        self.D_P_known_input.setEnabled(False)  # Default: disabled
        
        def toggle_d_p_input(checked):
            self.D_P_known_input.setEnabled(checked)
        
        # Signal verbinden
        self.D_P_checkbox.toggled.connect(toggle_d_p_input)
        
        # Add checkbox and input field for diffusion coefficient
        D_P_row = self._create_labeled_row("D<sub>P</sub>", "cm²/s", self.D_P_known_input)
        D_P_row.layout().insertWidget(3, self.D_P_checkbox)  # Add the checkbox in the row
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
        self.d_P_input = QLineEdit()
        self.d_F_input = QLineEdit()
        self.V_P_input = QLineEdit()
        self.V_F_input = QLineEdit()
        self.A_PF_input = QLineEdit()
        
        # Signale verbinden, damit sich die Felder automatisch ausfüllen
        self.d_P_input.textChanged.connect(self.update_geometric_inputs)
        self.V_P_input.textChanged.connect(self.update_geometric_inputs)
        self.d_F_input.textChanged.connect(self.update_geometric_inputs)
        self.V_F_input.textChanged.connect(self.update_geometric_inputs)
        self.A_PF_input.textChanged.connect(self.update_geometric_inputs)
        
        
        self.sim_case_dropdown = QComboBox()
        simulation_case = ["worst","best"]
        self.sim_case_dropdown.addItems(simulation_case)
        self.sim_case_dropdown.setMaximumWidth(85)

        # Narrow input fields
        for input_field in [self.d_P_input, self.d_F_input, self.V_P_input, self.V_F_input, self.A_PF_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower

        # Create rows for combined inputs
        row_1_layout = QHBoxLayout()
        row_1_layout.addWidget(self._create_labeled_row("A<sub>PF</sub>", "dm²", self.A_PF_input))
        row_1_layout.addWidget(self._create_labeled_row("Simulation Case", "", self.sim_case_dropdown))

        row_2_layout = QHBoxLayout()
        row_2_layout.addWidget(self._create_labeled_row("d<sub>P</sub>", "cm", self.d_P_input))
        row_2_layout.addWidget(self._create_labeled_row("d<sub>F</sub>", "cm", self.d_F_input))

        row_3_layout = QHBoxLayout()
        row_3_layout.addWidget(self._create_labeled_row("V<sub>P</sub>", "cm³", self.V_P_input))
        row_3_layout.addWidget(self._create_labeled_row("V<sub>F</sub>", "cm³", self.V_F_input))


        # Add rows to the form layout
        form_layout.addRow(row_1_layout)
        form_layout.addRow(row_2_layout)
        form_layout.addRow(row_3_layout)

        # Adjust spacing between rows
        form_layout.setVerticalSpacing(3)  # Adjust spacing between rows

        # Add form layout to the main layout
        geo_layout.addLayout(form_layout)

        return geo_layout
    
    def update_geometric_inputs(self):
        """Aktualisiert d_P, V_P, d_F und V_F dynamisch basierend auf Eingaben."""
        try:
            # Versuche, A_PF auszulesen
            A_PF = float(self.A_PF_input.text()) if self.A_PF_input.text() else None

            # Eingabewerte für d_P und V_P
            d_P = float(self.d_P_input.text()) if self.d_P_input.text() else None
            V_P = float(self.V_P_input.text()) if self.V_P_input.text() else None

            # Eingabewerte für d_F und V_F
            d_F = float(self.d_F_input.text()) if self.d_F_input.text() else None
            V_F = float(self.V_F_input.text()) if self.V_F_input.text() else None

            # Berechnungen nur durchführen, wenn A_PF vorhanden ist
            if A_PF is not None:
                # Berechnung für d_P und V_P
                if self.sender() == self.d_P_input and d_P is not None:
                    V_P = A_PF * d_P
                    self.V_P_input.blockSignals(True)
                    self.V_P_input.setText(f"{V_P:.4f}")
                    self.V_P_input.blockSignals(False)
                elif self.sender() == self.V_P_input and V_P is not None:
                    d_P = V_P / A_PF
                    self.d_P_input.blockSignals(True)
                    self.d_P_input.setText(f"{d_P:.4f}")
                    self.d_P_input.blockSignals(False)
                elif self.sender() == self.A_PF_input:
                    # A_PF wurde geändert, überprüfe und berechne neu
                    if d_P is not None:
                        V_P = A_PF * d_P
                        self.V_P_input.blockSignals(True)
                        self.V_P_input.setText(f"{V_P:.4f}")
                        self.V_P_input.blockSignals(False)
                    elif V_P is not None:
                        d_P = V_P / A_PF
                        self.d_P_input.blockSignals(True)
                        self.d_P_input.setText(f"{d_P:.4f}")
                        self.d_P_input.blockSignals(False)

                # Berechnung für d_F und V_F
                if self.sender() == self.d_F_input and d_F is not None:
                    V_F = A_PF * d_F
                    self.V_F_input.blockSignals(True)
                    self.V_F_input.setText(f"{V_F:.4f}")
                    self.V_F_input.blockSignals(False)
                elif self.sender() == self.V_F_input and V_F is not None:
                    d_F = V_F / A_PF
                    self.d_F_input.blockSignals(True)
                    self.d_F_input.setText(f"{d_F:.4f}")
                    self.d_F_input.blockSignals(False)
                elif self.sender() == self.A_PF_input:
                    # A_PF wurde geändert, überprüfe und berechne neu
                    if d_F is not None:
                        V_F = A_PF * d_F
                        self.V_F_input.blockSignals(True)
                        self.V_F_input.setText(f"{V_F:.4f}")
                        self.V_F_input.blockSignals(False)
                    elif V_F is not None:
                        d_F = V_F / A_PF
                        self.d_F_input.blockSignals(True)
                        self.d_F_input.setText(f"{d_F:.4f}")
                        self.d_F_input.blockSignals(False)

        except ValueError:
            # Wenn ein Wert ungültig ist, überspringe die Berechnung
            pass

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

    def validate_inputs(self):
        """Überprüft die Eingaben und markiert fehlerhafte Felder."""
        is_valid = True

        # Liste der Eingabefelder
        all_fields = {
            "T_C": self.T_C_input,
            "t_max": self.t_max_input,
            "M_r": self.M_r_input,
            "c_P0": self.c_P0_input,
            "P_density": self.P_density_input,
            "F_density": self.F_density_input,
            "D_P_known": self.D_P_known_input,
            "K_PF": self.K_PF_input,
            "dt": self.dt_input,
            "d_P": self.d_P_input,
            "V_P": self.V_P_input,
            "d_F": self.d_F_input,
            "V_F": self.V_F_input,
            "A_PF": self.A_PF_input,
        }

        for field_name, field in all_fields.items():
            if not self.is_valid_number(field.text()):
                is_valid = False
                self.mark_field_invalid(field)
            else:
                self.mark_field_valid(field)

        return is_valid

    def is_valid_number(self, value):
        """Prüft, ob der Wert eine gültige Dezimalzahl ist."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def mark_field_invalid(self, field):
        """Markiert ein Feld mit einer roten Umrandung, wenn es ungültig ist."""
        field.setStyleSheet("border: 1px solid red;")

    def mark_field_valid(self, field):
        """Entfernt die rote Umrandung, wenn das Feld gültig ist."""
        field.setStyleSheet("")

    def show_error_message(self, message):
        """Zeigt eine Fehlermeldung in der GUI an."""
        error_label = QLabel(message)
        error_label.setStyleSheet("color: red; font-weight: bold;")
        self.main_layout.addWidget(error_label)

    def start_calculation(self):
        """Führt die Berechnung basierend auf den Eingaben durch."""
        # Prüft ob Eingaben valide sind
        if not self.validate_inputs():
            self.show_error_message("Bitte korrigieren Sie die rot markierten Felder.")
            return
    
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
        d_P = float(self.d_P_input.text())
        V_P = float(self.V_P_input.text())
        d_F = float(self.d_P_input.text())
        V_F = float(self.V_P_input.text())

        # Geometrische Größen
        A_PF = float(self.A_PF_input.text())
        
        # Simulations-Case
        simulation_case = self.sim_case_dropdown.currentText()

        # Modellparameter nach Piringer
        dt = float(self.dt_input.text())

        # Berechnung der spez. Migrationsmenge
        results_area = migrationsmodell_piringer(M_r, T_C, c_P0, Material, P_density, F_density, K_PF, t_max, V_P, V_F, d_P, d_F, A_PF, dt, D_P_known, simulation_case)

        self.plot_results_area(results_area, t_max, dt)

    def plot_results_area(self, results_area, t_max, dt):
        """Zeigt die berechneten Ergebnisse im Berechnungs-Tab als Plot an."""
        self.figure.clear()  # Leere das aktuelle Plot-Fenster
        ax = self.figure.add_subplot(111)

        # Zeit in Tagen berechnen
        time_days = np.arange(0, t_max / (3600 * 24), dt / (3600 * 24))
        
        # Plot der Ergebnisse
        ax.plot(time_days, results_area, linewidth=2, color='#F06D1D')
        ax.set_xlabel('Zeit $[Tage]$', fontsize=14)
        ax.set_ylabel('spez. Migrationsmenge $[mg/dm^2]$', fontsize=14)
        ax.tick_params(axis='both', which='major', labelsize=14)

        # Plot aktualisieren
        self.canvas.draw()

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
