import csv
import os
from datetime import datetime

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog,
                               QGraphicsRectItem, QGraphicsScene,
                               QGraphicsView, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSizePolicy, QSpacerItem,
                               QTabWidget, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem)
from sl_model_functions import (calculate_max_cp0, migrationsmodell_piringer)
from tooltip_helper import DelayedToolTipHelper


class SingleLayerTab(QWidget):
    """
    GUI für das Single-Layer-Model. Organisiert in Tabs für Eingabe und Berechnung.
    """

    def __init__(self):
        super().__init__()

        self.tooltip_helper = DelayedToolTipHelper(parent=self)
        self.label_width = 50
        self.input_width = 90
        self.unit_width = 20
        self._validation_messages = []
        self.field_labels = {
            "T_C": "T_C",
            "t_max": "t_max",
            "M_r": "M_r",
            "c_P0": "cₚ₀",
            "P_density": "ρₚ",
            "F_density": "ρ_F",
            "D_P_known": "D_P",
            "K_PF": "K_PF",
            "dt": "Δt",
            "d_P": "d_P",
            "V_P": "V_P",
            "d_F": "d_F",
            "V_F": "V_F",
            "A_PF": "A_PF",
        }

        # Standardwerte für Initialgrafik
        self.default_d_P = 0.2  # Schichtdicke für Polymer Initialgrafik
        self.default_d_F = 2.5  # Schichtdicke für Fluid Initialgrafik

        # Standardwerte für Farben
        self.color_init_F = QColor("#64e6df")
        self.color_init_P = QColor("#f16d1d")

        self.rect_p = QGraphicsRectItem()  # Rechteck für Polymer
        self.rect_f = QGraphicsRectItem()  # Rechteck für Fluid

        # Farben für die grafische Darstellung der Schichten
        self.material_colors = {
            "LDPE": QColor("#f16d1d"),
            "LLDPE": QColor("#f16d1d"),
            "HDPE": QColor("#32c864"),
            "PP": QColor("#c832ee"),
            "PET": QColor("#646464"),
            "PS": QColor("#8c564b"),
            "PEN": Qt.darkCyan,
            "HIPS": Qt.darkBlue,
        }

        # Hauptlayout erstellen
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Fehlermeldung und Abstände hinzufügen
        self.error_label = QLabel("")  
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setWordWrap(True)
        self.main_layout.addWidget(self.error_label)

        # Dropdown für 3D-Plot-Parameter (initial None)
        self.plot_parameter_dropdown = None

        # Layouts für physikalisch/chemische Eingaben, geometrische Eingaben und Grafik
        sl_phy_chem_layout = self.create_phy_chem_inputs()
        sl_geo_layout = self.create_geo_inputs()
        sl_graphical_layout = self.create_grafical_setup()

        # Layout für die rechte Seite (geometrische Eingaben + Grafik)
        sl_input_tab_right_layout = QVBoxLayout()
        sl_input_tab_right_layout.addLayout(sl_geo_layout)
        sl_input_tab_right_layout.addLayout(sl_graphical_layout)

        # Hauptlayout horizontal kombinieren (linke und rechte Seite)
        sl_input_tab_layout = QHBoxLayout()
        sl_input_tab_layout.setSpacing(20)
        sl_input_tab_layout.setContentsMargins(0, 0, 0, 0)
        sl_input_tab_layout.addLayout(sl_phy_chem_layout, 1)  # Physikalisch-chemische Eingaben
        sl_input_tab_layout.addLayout(sl_input_tab_right_layout, 2)  # Geometrie + Grafik

        # Fertiges Layout hinzufügen
        self.main_layout.addLayout(sl_input_tab_layout)

    def create_phy_chem_inputs(self):
        # Create layout for physical/chemical inputs
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create a QLabel for the headline
        headline_label = QLabel("<b>Physikalische/chemische Größen</b>")
        headline_label.setAlignment(Qt.AlignLeft)
        headline_label.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(headline_label)

        # Inner layout controls spacing between inputs and headline
        inputs_layout = QVBoxLayout()
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(6)
        inputs_layout.setAlignment(Qt.AlignTop)

        # Add input fields
        self.T_C_input = QLineEdit("25")
        self.t_max_input = QLineEdit("1000")
        self.M_r_input = QLineEdit("136")
        self.c_P0_input = QLineEdit("100")
        self.P_density_input = QLineEdit("1")
        self.F_density_input = QLineEdit("1")
        self.D_P_known_input = QLineEdit()
        self.D_P_checkbox = QCheckBox("Bekannt")  # Checkbox to toggle D_P_known_input
        self.tooltip_helper.register(
            self.D_P_checkbox,
            "Aktivieren, um einen bekannten Diffusionskoeffizienten D_P einzugeben."
        )
        self.K_PF_input = QLineEdit("1")
        self.dt_input = QLineEdit("1")

        # Material dropdown
        material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]
        self.material_dropdown = QComboBox()
        self.material_dropdown.addItems(material_list)
        self._apply_input_width(self.material_dropdown)
        self.tooltip_helper.register(
            self.material_dropdown,
            "Material der betrachteten Polymerschicht auswählen."
        )

        # Narrow input fields
        for input_field in [self.T_C_input, self.t_max_input, self.M_r_input, self.c_P0_input,
                            self.P_density_input, self.F_density_input, self.D_P_known_input, self.K_PF_input, self.dt_input]:
            input_field.setFixedWidth(self.input_width)
            input_field.setFixedHeight(22)
            input_field.setAlignment(Qt.AlignRight)  # Text im Eingabefeld rechts ausrichten

        self.tooltip_helper.register(self.T_C_input, "Temperatur in °C.")
        self.tooltip_helper.register(self.t_max_input, "Gesamtdauer der Simulation.")
        self.tooltip_helper.register(self.dt_input, "Zeitschritt der Simulation.")
        self.tooltip_helper.register(self.M_r_input, "Relative Molekülmasse des Migranten.")
        self.tooltip_helper.register(self.c_P0_input, "Anfangskonzentration des Migranten im Polymer.")
        self.tooltip_helper.register(self.P_density_input, "Dichte des Polymers.")
        self.tooltip_helper.register(self.F_density_input, "Dichte der Kontaktphase.")
        self.tooltip_helper.register(self.K_PF_input, "Verteilungskoeffizient zwischen Polymer und Kontaktphase.")
        self.tooltip_helper.register(self.D_P_known_input, "Bekannter Diffusionskoeffizient.")
        
        # First row of the form
        inputs_layout.addWidget(self._create_labeled_row("Material", "", self.material_dropdown))
        # Other rows of the form
        inputs_layout.addWidget(self._create_labeled_row("T<sub>C</sub>", "°C", self.T_C_input))
        inputs_layout.addWidget(self._create_labeled_row("t<sub>max</sub>", "s", self.t_max_input))
        inputs_layout.addWidget(self._create_labeled_row("Δt", "s", self.dt_input))
        inputs_layout.addWidget(self._create_labeled_row("M<sub>r</sub>", "g/mol", self.M_r_input))
        inputs_layout.addWidget(self._create_labeled_row("c<sub>P0</sub>", "mg/kg", self.c_P0_input))
        inputs_layout.addWidget(self._create_labeled_row("ρ<sub>P</sub>", "g/cm³", self.P_density_input))
        inputs_layout.addWidget(self._create_labeled_row("ρ<sub>F</sub>", "g/cm³", self.F_density_input))
        inputs_layout.addWidget(self._create_labeled_row("K<sub>PF</sub>", "-", self.K_PF_input))
        
        
        # Zeile für die Eingabe des Diffusionskoeffizienten mir "Checkbox toggle"
        self.D_P_known_input.setEnabled(False)  # Default: disabled
        
        def toggle_d_p_input(checked):
            self.D_P_known_input.setEnabled(checked)
            self.validate_field(self.D_P_known_input, "D_P_known")
        
        # Signal verbinden
        self.D_P_checkbox.toggled.connect(toggle_d_p_input)
        
        # Add checkbox and input field for diffusion coefficient
        D_P_row = self._create_labeled_row("D<sub>P</sub>", "cm²/s", self.D_P_known_input)
        D_P_row.layout().insertWidget(3, self.D_P_checkbox)  # Add the checkbox in the row
        inputs_layout.addWidget(D_P_row)

        # Add configured input rows below the headline
        layout.addLayout(inputs_layout)
        layout.addStretch(1)

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

        return layout

    def create_geo_inputs(self):
        # Create layout for geometric inputs
        geo_layout = QVBoxLayout()
        geo_layout.setSpacing(6)
        geo_layout.setContentsMargins(0, 0, 0, 0)

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
        self.tooltip_helper.register(self.d_P_input, "Schichtdicke des Polymers.")
        self.tooltip_helper.register(self.d_F_input, "Schichtdicke der Kontaktphase.")
        self.tooltip_helper.register(self.V_P_input, "Volumen des Polymers.")
        self.tooltip_helper.register(self.V_F_input, "Volumen der Kontaktphase.")
        self.tooltip_helper.register(self.A_PF_input, "Kontaktfläche zwischen Polymer und Kontaktphase.")
        
        
        # Signale verbinden, damit sich die Felder automatisch ausfüllen
        self.d_P_input.textChanged.connect(self.update_geometric_inputs)
        self.V_P_input.textChanged.connect(self.update_geometric_inputs)
        self.d_F_input.textChanged.connect(self.update_geometric_inputs)
        self.V_F_input.textChanged.connect(self.update_geometric_inputs)
        self.A_PF_input.textChanged.connect(self.update_geometric_inputs)
        
        self.sim_case_dropdown = QComboBox()
        simulation_case = ["worst","best"]
        self.sim_case_dropdown.addItems(simulation_case)
        self._apply_input_width(self.sim_case_dropdown)
        self.tooltip_helper.register(
            self.sim_case_dropdown,
            "Bestimmt, ob mit Worst-Case- oder Best-Case-Annahmen gerechnet wird (Diffusionskoeffizient nach Piringer)."
        )

        # Narrow input fields
        for input_field in [self.d_P_input, self.d_F_input, self.V_P_input, self.V_F_input, self.A_PF_input]:
            self._apply_input_width(input_field)
            input_field.setFixedHeight(22)
            input_field.setAlignment(Qt.AlignRight)  # Text im Eingabefeld rechts ausrichten

        # Create rows for combined inputs
        row_1_layout = QHBoxLayout()
        row_1_layout.setSpacing(12)
        row_1_layout.addWidget(self._create_labeled_row("A<sub>PF</sub>", "dm²", self.A_PF_input))
        row_1_layout.addWidget(self._create_labeled_row("Simulation Case", "", self.sim_case_dropdown))

        row_2_layout = QHBoxLayout()
        row_2_layout.setSpacing(12)
        row_2_layout.addWidget(self._create_labeled_row("d<sub>P</sub>", "cm", self.d_P_input))
        row_2_layout.addWidget(self._create_labeled_row("d<sub>F</sub>", "cm", self.d_F_input))

        row_3_layout = QHBoxLayout()
        row_3_layout.setSpacing(12)
        row_3_layout.addWidget(self._create_labeled_row("V<sub>P</sub>", "cm³", self.V_P_input))
        row_3_layout.addWidget(self._create_labeled_row("V<sub>F</sub>", "cm³", self.V_F_input))

        # Add rows to the form layout
        geo_layout.addLayout(row_1_layout)
        geo_layout.addLayout(row_2_layout)
        geo_layout.addLayout(row_3_layout)
        
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
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)

        # Rechtecke in der Szene hinzufügen (mit Standardwerten)
        self.rect_f.setRect(0, 0, self.default_d_F * 40, 200)  # Skalierung *20 für Sichtbarkeit
        self.rect_f.setBrush(self.color_init_F)
        self.graphics_scene.addItem(self.rect_f)

        self.rect_p.setRect(0, 0, self.default_d_P * 40, 200)
        self.rect_p.setBrush(self.color_init_P)
        self.graphics_scene.addItem(self.rect_p)

        # Grafikbereich hinzufügen
        layout.addWidget(self.graphics_view)
        
        # Neues Layout für Error-Meldung und Start Button
        error_button_layout = QHBoxLayout()
        self.error_label.setFixedHeight(30)
        error_button_layout.addWidget(self.error_label, 1)
        
        # Button hinzufügen
        start_button = QPushButton("Berechnung starten")
        start_button.setFixedSize(150, 30)  # Button-Größe anpassen
        start_button.clicked.connect(self.start_calculation)  # Signal verbinden
        error_button_layout.addWidget(start_button, 0)

        # 3D-Plot Migration Button hinzufügen
        plot_surface_button = QPushButton("Parameter 3D-Plot")
        plot_surface_button.setFixedSize(180, 30)
        plot_surface_button.clicked.connect(self.plot_migration_surface)
        error_button_layout.addWidget(plot_surface_button, 0)

        layout.addLayout(error_button_layout)
        
        return layout

    def plot_migration_surface(self):
        from sl_model_functions import plot_migration_surface_over_parameter
        from PySide6.QtWidgets import QInputDialog, QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, QLineEdit

        if not self.validate_inputs():
            self.show_error_message("Bitte korrigieren Sie die rot markierten Felder.")
            return

        # Basiseingaben auslesen
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
        d_F = float(self.d_F_input.text())
        V_F = float(self.V_F_input.text())
        A_PF = float(self.A_PF_input.text())
        dt = float(self.dt_input.text())
        simulation_case = self.sim_case_dropdown.currentText()

        # Benutzer fragen, welcher Parameter variiert werden soll
        parameter, ok = QInputDialog.getItem(
            self,
            "Parameter für 3D-Plot",
            "Welcher Parameter soll variiert werden?",
            ["T_C", "M_r", "c_P0", "P_density", "F_density", "K_PF", "V_P", "V_F", "d_P", "d_F", "A_PF"],
            0,
            False
        )
        if not ok or not parameter:
            return

        # Dialog zur Eingabe von min, max, steps
        class ParameterRangeDialog(QDialog):
            def __init__(self, parameter_name, parent=None):
                super().__init__(parent)
                self.setWindowTitle(f"{parameter_name} Bereich definieren")
                self.min_input = QLineEdit()
                self.max_input = QLineEdit()
                self.steps_input = QLineEdit("6")

                form_layout = QFormLayout()
                form_layout.addRow(f"{parameter_name} Minimum:", self.min_input)
                form_layout.addRow(f"{parameter_name} Maximum:", self.max_input)
                form_layout.addRow("Anzahl Schritte:", self.steps_input)

                buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                buttons.accepted.connect(self.accept)
                buttons.rejected.connect(self.reject)

                layout = QVBoxLayout()
                layout.addLayout(form_layout)
                layout.addWidget(buttons)
                self.setLayout(layout)

            def get_values(self):
                return float(self.min_input.text()), float(self.max_input.text()), int(self.steps_input.text())

        # Erstelle und zeige den Dialog
        dialog = ParameterRangeDialog(parameter, self)
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            min_val, max_val, steps = dialog.get_values()
        except ValueError:
            self.show_error_message("Ungültige Eingaben im Parameterbereich.")
            return

        param_range = list(np.linspace(min_val, max_val, steps))

        # Parameterdictionary
        fixed_params = {
            "M_r": M_r,
            "T_C": T_C,
            "c_P0": c_P0,
            "Material": Material,
            "P_density": P_density,
            "F_density": F_density,
            "K_PF": K_PF,
            "t_max": t_max,
            "V_P": V_P,
            "V_F": V_F,
            "d_P": d_P,
            "d_F": d_F,
            "A_PF": A_PF,
            "dt": dt,
            "D_P_known": D_P_known,
            "simulation_case": simulation_case
        }

        plot_migration_surface_over_parameter(parameter, param_range, fixed_params)

    def update_graphics(self):
        """Aktualisiert die Breite, Farbe und Position der Rechtecke basierend auf Eingaben."""
        try:
            # Eingabewerte abrufen
            d_P = float(self.d_P_input.text()) if self.d_P_input.text() else self.default_d_P
            d_F = float(self.d_F_input.text()) if self.d_F_input.text() else self.default_d_F

            # Skalierungsfaktor für die Rechteckgröße
            scaling_factor = 40
            width_p = d_P * scaling_factor
            width_f = d_F * scaling_factor
            total_width = width_p + width_f

            # Szenenmitte berechnen
            scene_width = self.graphics_scene.width()
            scene_height = self.graphics_scene.height()

            center_x = scene_width / 2
            center_y = scene_height / 2

            # Berechnung der Startposition für die Rechtecke
            start_x = center_x - (total_width / 2)  # Zentriere beide Rechtecke horizontal
            start_y = center_y - 100  # Rechtecke vertikal zentrieren (200 ist die Rechteckhöhe)

            # Rechtecke setzen
            self.rect_p.setRect(start_x, start_y, width_p, 200)
            self.rect_f.setRect(start_x + width_p, start_y, width_f, 200)

            # Farbe des Polymers basierend auf Material aktualisieren
            material = self.material_dropdown.currentText()
            color = self.material_colors.get(material, Qt.red)  # Fallback zu Rot
            self.rect_p.setBrush(color)

        except ValueError:
            # Ungültige Eingaben ignorieren
            pass

    def validate_inputs(self):
        """Überprüft die Eingaben und markiert fehlerhafte Felder."""
        is_valid = True
        self._validation_messages = []

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
        else:
            message = self._compose_validation_message()
            self.show_error_message(message)

        return is_valid
    
    def validate_field(self, field, field_name):
        """Überprüft ein einzelnes Eingabefeld auf Gültigkeit."""
        if not self.is_valid_number(field.text(), field_name, set_message=False):
            self.mark_field_invalid(field)
        else:
            self.mark_field_valid(field)

    def is_valid_number(self, value, field_name, set_message=True):
        """Prüft, ob der Wert eine gültige Dezimalzahl ist."""
        # Sonderfall für D_P: Nur prüfen, wenn Checkbox aktiviert ist
        if field_name == "D_P_known" and not self.D_P_checkbox.isChecked():
            return True  # Keine Validierung erforderlich
        if not value.strip():
            if set_message:
                self._add_validation_message(f"{self.field_labels.get(field_name, field_name)} darf nicht leer sein.")
            return False
        if "," in value:
            if set_message:
                self._add_validation_message("Bitte '.' als Dezimaltrennzeichen verwenden.")
            return False
        try:
            float(value.strip())
            return True
        except ValueError:
            if set_message:
                self._add_validation_message(f"{self.field_labels.get(field_name, field_name)} muss eine Zahl sein.")
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

    def _add_validation_message(self, message):
        if message not in self._validation_messages:
            self._validation_messages.append(message)

    def _compose_validation_message(self):
        if not self._validation_messages:
            return "Bitte korrigieren Sie die rot markierten Felder."
        if len(self._validation_messages) == 1:
            return self._validation_messages[0]
        return " • ".join(self._validation_messages)

    def start_calculation(self):
        """Führt die Berechnung basierend auf den Eingaben durch."""
        # Prüft ob Eingaben valide sind
        if not self.validate_inputs():
            self.show_error_message("Bitte korrigiere alle rot markierten Felder.")
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
        row_layout = QHBoxLayout()
        row_layout.setSpacing(4)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"<html>{label_text}</html>")
        label.setMinimumWidth(self.label_width)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        if isinstance(input_field, QLineEdit):
            self._apply_input_width(input_field)
            input_field.setFixedHeight(22)
            input_field.setAlignment(Qt.AlignRight)
        elif isinstance(input_field, QComboBox):
            input_field.setFixedHeight(24)
            self._apply_input_width(input_field)

        unit_label = QLabel(unit_text)
        unit_label.setMinimumWidth(self.unit_width)
        unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unit_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        row_layout.addWidget(label)
        row_layout.addWidget(input_field)
        row_layout.addWidget(unit_label)
        row_layout.addStretch(1)

        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        return row_widget

    def _init_dimension_defaults(self):
        label_texts = [
            "Material", "T<sub>C</sub>", "t<sub>max</sub>", "Δt",
            "M<sub>r</sub>", "c<sub>P0</sub>", "ρ<sub>P</sub>", "ρ<sub>F</sub>",
            "K<sub>PF</sub>", "D<sub>P</sub>", "A<sub>PF</sub>", "d<sub>P</sub>",
            "d<sub>F</sub>", "V<sub>P</sub>", "V<sub>F</sub>", "Simulation Case"
        ]
        unit_texts = [
            "°C", "s", "g/mol", "mg/kg", "g/cm³", "-", "cm²/s",
            "dm²", "cm", "cm³", ""
        ]

        self.label_width = self._compute_html_label_width(label_texts) + 6
        self.unit_width = max(self._compute_html_label_width(unit_texts), 55)
        self.input_width = 90

    def _compute_html_label_width(self, texts):
        max_width = 0
        for text in texts:
            if not text:
                continue
            label = QLabel(f"<html>{text}</html>")
            label.setTextFormat(Qt.RichText)
            max_width = max(max_width, label.sizeHint().width())
        return max_width

    def _apply_input_width(self, widget):
        widget.setFixedWidth(self.input_width)
        if isinstance(widget, QComboBox):
            widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)


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
