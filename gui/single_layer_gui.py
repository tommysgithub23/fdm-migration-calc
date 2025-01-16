import csv
import os
from datetime import datetime

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGraphicsRectItem, QGraphicsScene,
                               QGraphicsView, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSizePolicy, QSpacerItem,
                               QTabWidget, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem)
from sl_model_functions import (calculate_max_cp0, migrationsmodell_piringer)


class SingleLayerTab(QWidget):
    """
    GUI für das Single-Layer-Model. Organisiert in Tabs für Eingabe und Berechnung.
    """
    def __init__(self):
        super().__init__()
        
        # Standardwerte für Initialgrafik
        self.default_d_P = 0.2  # Schichtdicke für Polymer Initalgrafik
        self.default_d_F = 2.5  # Schichtdicke für Fluid Initialgrafik
        
        # Standarwerte für Farben
        self.color_init_F = QColor("#64e6df")
        self.color_init_P = QColor("#f16d1d")
        
        self.rect_p = QGraphicsRectItem()  # Rechteck für Polymier
        self.rect_f = QGraphicsRectItem()  # Rechteck für Fluid

        # Farben für die grafische Darstellung der Schichten (noch anpassen!)
        self.material_colors = {
            "LDPE": Qt.green,
            "LLDPE": Qt.darkGreen,
            "HDPE": Qt.cyan,
            "PP": Qt.yellow,
            "PET": Qt.magenta,
            "PS": Qt.gray,
            "PEN": Qt.darkCyan,
            "HIPS": Qt.darkBlue
        }
                
        # Hauptlayout erstellen
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Sub-Tab-Widget für Eingabe und Berechnung
        self.sl_sub_tab_widget = QTabWidget()

        # Zentrales Lable für die Fehlermeldung
        self.error_label = QLabel("")  
        self.error_label.setStyleSheet("color: red; font-weight: bold;")  
        self.error_label.setWordWrap(True)  # Falls nötig, kann die Meldung umgebrochen werden

        # Tabs hinzufügen
        self.create_input_tab()

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

    def create_phy_chem_inputs(self):
        # Create layout for physical/chemical inputs
        form_layout = QFormLayout()

        # Create a QLabel for the headline
        headline_label = QLabel("<b>Physikalische/chemische Größen</b>")
        headline_label.setAlignment(Qt.AlignLeft)  # Align left like the form layout rows
        headline_label.setContentsMargins(0, 0, 0, 0)  # Remove any additional margins
        form_layout.addRow(headline_label)  # Add headline directly to the form layout

        # Add input fields
        self.T_C_input = QLineEdit("25")
        self.t_max_input = QLineEdit("1000")
        self.M_r_input = QLineEdit("136")
        self.c_P0_input = QLineEdit("100")
        self.P_density_input = QLineEdit("1")
        self.F_density_input = QLineEdit("1")
        self.D_P_known_input = QLineEdit()
        self.D_P_checkbox = QCheckBox("Bekannt")  # Checkbox to toggle D_P_known_input
        self.K_PF_input = QLineEdit("1")
        self.dt_input = QLineEdit("1")

        # Material dropdown
        material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]
        self.material_dropdown = QComboBox()
        self.material_dropdown.addItems(material_list)      

        # Narrow input fields
        for input_field in [self.T_C_input, self.t_max_input, self.M_r_input, self.c_P0_input, 
                            self.P_density_input, self.F_density_input, self.D_P_known_input, self.K_PF_input, self.dt_input]:
            input_field.setMaximumWidth(70)  # Set max width to make fields narrower
            input_field.setAlignment(Qt.AlignRight)  # Text im Eingabefeld rechts ausrichten
        
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
        
        # Dynamische Validierung für physikalisch-chemische Eingabefelder (Verbindet Feld mit Signal)
        self.T_C_input.textChanged.connect(lambda: self.validate_field(self.T_C_input, "T_C"))
        self.t_max_input.textChanged.connect(lambda: self.validate_field(self.t_max_input, "t_max"))
        self.M_r_input.textChanged.connect(lambda: self.validate_field(self.M_r_input, "M_r"))
        self.c_P0_input.textChanged.connect(lambda: self.validate_field(self.c_P0_input, "c_P0"))
        self.P_density_input.textChanged.connect(lambda: self.validate_field(self.P_density_input, "P_density"))
        self.F_density_input.textChanged.connect(lambda: self.validate_field(self.F_density_input, "F_density"))
        self.D_P_known_input.textChanged.connect(lambda: self.validate_field(self.D_P_known_input, "D_P_known"))
        self.K_PF_input.textChanged.connect(lambda: self.validate_field(self.K_PF_input, "K_PF"))
        self.dt_input.textChanged.connect(lambda: self.validate_field(self.dt_input, "dt"))
        
        # Dynamisches Anpassen der Schichtdarstellugn basierend auf Material 
        self.material_dropdown.currentTextChanged.connect(self.update_graphics)

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
        self.d_P_input = QLineEdit("0.2")
        self.d_F_input = QLineEdit("2")
        self.V_P_input = QLineEdit("1.2")
        self.V_F_input = QLineEdit("11")
        self.A_PF_input = QLineEdit("6")
        
        
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
            input_field.setAlignment(Qt.AlignRight)  # Text im Eingabefeld rechts ausrichten

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
        
        # Dynamische Validierung für geometrische Eingabefelder
        self.d_P_input.textChanged.connect(lambda: self.validate_field(self.d_P_input, "d_P"))
        self.d_F_input.textChanged.connect(lambda: self.validate_field(self.d_F_input, "d_F"))
        self.V_P_input.textChanged.connect(lambda: self.validate_field(self.V_P_input, "V_P"))
        self.V_F_input.textChanged.connect(lambda: self.validate_field(self.V_F_input, "V_F"))
        self.A_PF_input.textChanged.connect(lambda: self.validate_field(self.A_PF_input, "A_PF"))
        
        # Dynamisches Anpassen der Schichtdarstellugn basierend auf Schichtdicke
        self.d_P_input.textChanged.connect(self.update_geometric_inputs)
        self.V_P_input.textChanged.connect(self.update_geometric_inputs)
        self.d_F_input.textChanged.connect(self.update_geometric_inputs)
        self.V_F_input.textChanged.connect(self.update_geometric_inputs)
        self.A_PF_input.textChanged.connect(self.update_geometric_inputs)

        return geo_layout
    
    def update_geometric_inputs(self):
        """Aktualisiert d_P, V_P, d_F und V_F dynamisch basierend auf Eingaben."""
        try:
            # Eingabewerte abrufen
            A_PF = float(self.A_PF_input.text()) if self.A_PF_input.text().strip() else None
            d_P = float(self.d_P_input.text()) if self.d_P_input.text().strip() else None
            V_P = float(self.V_P_input.text()) if self.V_P_input.text().strip() else None
            d_F = float(self.d_F_input.text()) if self.d_F_input.text().strip() else None
            V_F = float(self.V_F_input.text()) if self.V_F_input.text().strip() else None

            sender = self.sender()  # Das Feld, das das Signal ausgelöst hat

            if sender == self.A_PF_input and A_PF is not None:
                # Aktualisiere d_P und V_P basierend auf A_PF
                if d_P is not None:
                    V_P = A_PF * d_P
                    self.V_P_input.blockSignals(True)
                    self.V_P_input.setText(f"{V_P:.2f}")
                    self.V_P_input.blockSignals(False)
                elif V_P is not None:
                    d_P = V_P / A_PF
                    self.d_P_input.blockSignals(True)
                    self.d_P_input.setText(f"{d_P:.2f}")
                    self.d_P_input.blockSignals(False)

                # Aktualisiere d_F und V_F basierend auf A_PF
                if d_F is not None:
                    V_F = A_PF * d_F
                    self.V_F_input.blockSignals(True)
                    self.V_F_input.setText(f"{V_F:.2f}")
                    self.V_F_input.blockSignals(False)
                elif V_F is not None:
                    d_F = V_F / A_PF
                    self.d_F_input.blockSignals(True)
                    self.d_F_input.setText(f"{d_F:.2f}")
                    self.d_F_input.blockSignals(False)

            elif sender == self.d_P_input and d_P is not None and A_PF is not None:
                V_P = A_PF * d_P
                self.V_P_input.blockSignals(True)
                self.V_P_input.setText(f"{V_P:.2f}")
                self.V_P_input.blockSignals(False)

            elif sender == self.V_P_input and V_P is not None and A_PF is not None:
                d_P = V_P / A_PF
                self.d_P_input.blockSignals(True)
                self.d_P_input.setText(f"{d_P:.2f}")
                self.d_P_input.blockSignals(False)

            elif sender == self.d_F_input and d_F is not None and A_PF is not None:
                V_F = A_PF * d_F
                self.V_F_input.blockSignals(True)
                self.V_F_input.setText(f"{V_F:.2f}")
                self.V_F_input.blockSignals(False)

            elif sender == self.V_F_input and V_F is not None and A_PF is not None:
                d_F = V_F / A_PF
                self.d_F_input.blockSignals(True)
                self.d_F_input.setText(f"{d_F:.2f}")
                self.d_F_input.blockSignals(False)

            # Aktualisiere die grafische Darstellung
            self.update_graphics()

        except ValueError:
            # Überspringe Berechnungen, wenn ungültige Werte vorhanden sind
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

        # Rechtecke in der Szene hinzufügen (mit Standardwerten)
        self.rect_f.setRect(0, 0, self.default_d_F * 40, 200)  # Skalierung *20 für Sichtbarkeit
        self.rect_f.setBrush(self.color_init_F)
        graphics_scene.addItem(self.rect_f)

        self.rect_p.setRect(0, 0, self.default_d_P * 40, 200)
        self.rect_p.setBrush(self.color_init_P)
        graphics_scene.addItem(self.rect_p)

        # Grafikbereich hinzufügen
        layout.addWidget(graphics_view)
        
        # Neues Layout für Error-Meldung und Start Button
        error_button_layout = QHBoxLayout()
        self.error_label.setFixedHeight(30)
        error_button_layout.addWidget(self.error_label, 1)
        
        # Button hinzufügen
        start_button = QPushButton("Berechnung starten")
        start_button.setFixedSize(150, 30)  # Button-Größe anpassen
        start_button.clicked.connect(self.start_calculation)  # Signal verbinden
        error_button_layout.addWidget(start_button, 0)

        layout.addLayout(error_button_layout)
        
        return layout

    def update_graphics(self):
        """Aktualisiert die Breite und Farbe der Rechtecke basierend auf Eingaben."""
        try:
            # Werte für d_P und d_F abrufen
            d_P = float(self.d_P_input.text()) if self.d_P_input.text() else self.default_d_P
            d_F = float(self.d_F_input.text()) if self.d_F_input.text() else self.default_d_F

            # Begrenzung der Maximalbreite
            max_width = 400
            total_width = d_P + d_F
            scaling_factor = min(40, max_width / total_width)

            # Rechteckbreite berechnen
            width_p = d_P * scaling_factor
            width_f = d_F * scaling_factor
            total_scaled_width = width_p + width_f

            # Zentrierung der Rechtecke
            offset = (max_width - total_scaled_width) / 2
            self.rect_p.setRect(offset, 0, width_p, 200)
            self.rect_f.setRect(offset + width_p, 0, width_f, 200)

            # Farbe des linken Rechtecks basierend auf Material
            material = self.material_dropdown.currentText()
            color = self.material_colors.get(material, Qt.red)  # Fallback zu Rot
            self.rect_p.setBrush(color)

        except ValueError:
            pass  # Überspringe ungültige Werte


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
            if not self.is_valid_number(field.text(), field_name):
                is_valid = False
                self.mark_field_invalid(field)
            else:
                self.mark_field_valid(field)
                
        if is_valid: 
            self.error_label.setText("") # Löscht Fehlermeldung

        return is_valid
    
    def validate_field(self, field, field_name):
        """Überprüft ein einzelnes Eingabefeld auf Gültigkeit."""
        if not self.is_valid_number(field.text(), field_name):
            self.mark_field_invalid(field)
        else:
            self.mark_field_valid(field)

    def is_valid_number(self, value, field_name):
        """Prüft, ob der Wert eine gültige Dezimalzahl ist."""
        # Sonderfall für D_P: Nur prüfen, wenn Checkbox aktiviert ist
        if field_name == "D_P_known" and not self.D_P_checkbox.isChecked():
            return True  # Keine Validierung erforderlich
        if not value.strip():
            return False
        try:
            float(value.strip())
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
        self.error_label.setText(message)  # Setze die Fehlermeldung in das zentrale QLabel

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

        # Popup-Fenster öffnen
        self.results_popup = ResultsPopup(results_area, t_max, dt)
        self.results_popup.show()

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


class ResultsPopup(QWidget):
    def __init__(self, results_area, t_max, dt):
        super().__init__()
        self.setWindowTitle("Berechnungsergebnisse")
        self.setGeometry(100, 100, 800, 600)  # Fenstergröße setzen

        self.results_area = results_area
        self.t_max = t_max
        self.dt = dt

        layout = QVBoxLayout(self)

        # Matplotlib-Canvas für Plot
        self.figure = Figure(figsize=(11, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Zusammenfassung
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Layout für Buttons
        button_layout = QHBoxLayout()

        # Platzhalter für Abstand nach links
        button_layout.addStretch()

        # Export-Button für Ergebnisse (CSV)
        export_csv_button = QPushButton("Ergebnisse als CSV exportieren")
        export_csv_button.setFixedSize(200, 40)  # Größe des Buttons anpassen
        export_csv_button.clicked.connect(self.export_results)
        button_layout.addWidget(export_csv_button)

        # Export-Button für Plot (PDF)
        export_pdf_button = QPushButton("Plot als PDF exportieren")
        export_pdf_button.setFixedSize(200, 40)  # Größe des Buttons anpassen
        export_pdf_button.clicked.connect(self.export_plot)
        button_layout.addWidget(export_pdf_button)

        layout.addLayout(button_layout)

        # Daten in die Widgets einfügen
        self.update_summary()
        self.plot_results_area()

    def update_summary(self):
        """Zeigt eine Zusammenfassung der Ergebnisse."""
        max_migration = max(self.results_area)
        summary = f"""
        <b>Zusammenfassung:</b><br>
        Maximale Migration: {max_migration:.2f} mg/dm²<br>
        Simulierte Zeit: {self.t_max / (3600 * 24):.2f} Tage
        """
        self.summary_label.setText(summary)

    def plot_results_area(self):
        """Erstellt den Plot der Berechnungsergebnisse."""
        time_days = np.linspace(0, self.t_max / (3600 * 24), len(self.results_area))

        # Adjust plot position and margins
        # self.figure.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)

        ax = self.figure.add_subplot(111)
        ax.clear()
        ax.plot(time_days, self.results_area, linewidth=2, color='#F06D1D')
        ax.set_xlabel('Zeit $[Tage]$', fontsize=11)
        ax.set_ylabel('spez. Migrationsmenge $[mg/dm^2]$', fontsize=11)
        ax.tick_params(axis='both', which='major', labelsize=11)
        self.canvas.draw()

    def export_results(self):
        """Exportiert die Ergebnisse als CSV-Datei."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Ergebnisse exportieren", "", "CSV-Dateien (*.csv)")
        if file_path:
            with open(file_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Zeit (Tage)", "Migration (mg/dm²)"])
                time_days = np.arange(0, self.t_max / (3600 * 24), self.dt / (3600 * 24))
                for time, result in zip(time_days, self.results_area):
                    writer.writerow([time, result])

    def export_plot(self):
        """Exportiert den Plot als PDF-Datei."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Plot als PDF exportieren", "", "PDF-Dateien (*.pdf)")
        if file_path:
            self.figure.savefig(file_path, format="pdf")
