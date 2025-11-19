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
from sl_model_package.EFSA_extended import (
    generate_curves,
    compute_cmod_efsa,
    compute_eta_min_efsa,
    DEFAULT_MATERIAL,
)
from sl_model_functions import (
    calculate_max_cp0,
    migrationsmodell_piringer,
    plot_migration_surface_over_parameter,
)
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

        # Initiale grafische Darstellung aktualisieren
        self.update_graphics()

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
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Überschrift
        headline_label = QLabel("<b>Grafische Darstellung der Schichten</b>")
        headline_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(headline_label)

        # Grafikbereich
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setFixedHeight(220)
        self.graphics_view.setMaximumWidth(360)
        self.graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Rechtecke in der Szene hinzufügen (mit Standardwerten)
        self.rect_f.setRect(0, 0, self.default_d_F * 40, 100)
        self.rect_f.setBrush(self.color_init_F)
        self.graphics_scene.addItem(self.rect_f)

        self.rect_p.setRect(0, 0, self.default_d_P * 40, 100)
        self.rect_p.setBrush(self.color_init_P)
        self.graphics_scene.addItem(self.rect_p)

        # Grafikbereich hinzufügen
        layout.addWidget(self.graphics_view)
        
        # Neues Layout für Error-Meldung und Start Button
        error_button_layout = QHBoxLayout()
        self.error_label.setFixedHeight(30)
        error_button_layout.addWidget(self.error_label, 1)
        
        # Button hinzufügen
        self.start_button = QPushButton("Berechnung starten")
        self.start_button.setMinimumWidth(150)
        self.start_button.setFixedHeight(28)
        self.start_button.clicked.connect(self.start_calculation)  # Signal verbinden
        error_button_layout.addWidget(self.start_button, 0)

        # (Entfernt: 3D-Plot Migration Button)

        layout.addLayout(error_button_layout)
        
        return layout

    def plot_migration_surface(self):
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
            width_p = max(0, d_P * scaling_factor)
            width_f = max(0, d_F * scaling_factor)
            height = 100
            x_offset = 0

            self.graphics_scene.clear()

            # Polymerschicht
            material = self.material_dropdown.currentText()
            color = self.material_colors.get(material, Qt.red)  # Fallback zu Rot
            self.rect_p = self.graphics_scene.addRect(x_offset, 0, width_p, height)
            self.rect_p.setBrush(color)
            self.rect_p.setToolTip(f"Polymer ({material}): {d_P} cm")
            x_offset += width_p

            # Kontaktphase
            self.rect_f = self.graphics_scene.addRect(x_offset, 0, width_f, height)
            self.rect_f.setBrush(self.color_init_F)
            self.rect_f.setToolTip(f"Kontaktphase: {d_F} cm")

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


class ParameterVariationPopup(QWidget):
    """Popup-Fenster zur Darstellung der Parametervariation."""

    def __init__(self, parameter_name, parameter_values, fixed_params, simulation_case):
        super().__init__()
        self.parameter_name = parameter_name
        self.parameter_values = parameter_values
        self.fixed_params = fixed_params
        self.simulation_case = simulation_case

        self.setWindowTitle("Parametervariation")
        self.setGeometry(120, 120, 900, 650)

        layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(11, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self._plot_surface()
        self._update_summary()

    def _plot_surface(self):
        self.figure.clear()
        plot_migration_surface_over_parameter(
            self.parameter_name,
            self.parameter_values,
            self.fixed_params,
            simulation_case=self.simulation_case,
            figure=self.figure,
            show=False,
        )
        self.canvas.draw()

    def _update_summary(self):
        if not self.parameter_values:
            return
        summary = (
            f"<b>Parameter:</b> {self.parameter_name}<br>"
            f"<b>Bereich:</b> {self.parameter_values[0]:.3g} – {self.parameter_values[-1]:.3g}"
            f" ({len(self.parameter_values)} Schritte)"
        )
        self.summary_label.setText(summary)


class EFSAExtendedTab(QWidget):
    """
    EFSA-Tool als Unter-Tab im Single-Layer-Bereich.
    Berechnet C_mod und eta_min über einen Molekulargewichtsbereich,
    erlaubt den Import von Messwerten (CSV/Excel) zur Überlagerung.
    """

    def __init__(self):
        super().__init__()
        self.measurement_points = []  # Liste von Dicts mit keys: Mr, C_mod, eta_min (optional)
        self._fields = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(12, 12, 12, 12)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setWordWrap(True)
        self.main_layout.addWidget(self.error_label)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        self.main_layout.addLayout(top_layout)

        # Eingabefelder
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(["A", "B", "C"])
        self.mr_min_input = QLineEdit("80")
        self.mr_max_input = QLineEdit("500")
        self.points_input = QLineEdit("400")
        self.c_ref_input = QLineEdit("3.0")
        self.material_combo = QComboBox()
        self.material_combo.addItems(["PET", "LDPE", "LLDPE", "HDPE", "PP", "PS", "PEN", "HIPS"])

        for fld in (self.mr_min_input, self.mr_max_input, self.points_input, self.c_ref_input):
            fld.setFixedWidth(90)
            fld.setAlignment(Qt.AlignRight)
            fld.setFixedHeight(24)
            self._fields.append(fld)

        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.addWidget(self._create_labeled_row("Material", "", self.material_combo))
        left_col.addWidget(self._create_labeled_row("Szenario", "", self.scenario_combo))
        left_col.addWidget(self._create_labeled_row("M<sub>r,min</sub>", "g/mol", self.mr_min_input))
        left_col.addWidget(self._create_labeled_row("M<sub>r,max</sub>", "g/mol", self.mr_max_input))
        left_col.addWidget(self._create_labeled_row("Anzahl Punkte", "", self.points_input))
        left_col.addWidget(self._create_labeled_row("c<sub>ref</sub>", "mg/kg", self.c_ref_input))

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        import_btn = QPushButton("Messwerte importieren")
        import_btn.setFixedHeight(26)
        import_btn.clicked.connect(self._import_measurements)
        calc_btn = QPushButton("Berechnen")
        calc_btn.setFixedHeight(26)
        calc_btn.clicked.connect(self.update_plots)
        export_btn = QPushButton("Plots exportieren")
        export_btn.setFixedHeight(26)
        export_btn.clicked.connect(self._export_plots)
        button_row.addWidget(import_btn)
        button_row.addWidget(calc_btn)
        button_row.addWidget(export_btn)
        button_row.addStretch()
        left_col.addLayout(button_row)
        left_col.addStretch()

        top_layout.addLayout(left_col, 0)

        # Plot-Bereich
        plots_layout = QVBoxLayout()
        plots_layout.setSpacing(12)
        plots_layout.setContentsMargins(0, 0, 0, 0)

        self.cmod_figure = Figure(figsize=(6, 4))
        self.cmod_canvas = FigureCanvas(self.cmod_figure)
        plots_layout.addWidget(self.cmod_canvas)

        self.eta_figure = Figure(figsize=(6, 4))
        self.eta_canvas = FigureCanvas(self.eta_figure)
        plots_layout.addWidget(self.eta_canvas)

        top_layout.addLayout(plots_layout, 1)

        self.update_plots()

    def _create_labeled_row(self, label_text: str, unit_text: str, widget: QWidget) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"<html>{label_text}</html>")
        label.setMinimumWidth(80)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unit = QLabel(unit_text)
        unit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unit.setMinimumWidth(40)

        row.addWidget(label)
        row.addWidget(widget)
        row.addWidget(unit)
        row.addStretch()

        container = QWidget()
        container.setLayout(row)
        return container

    def _parse_float(self, field: QLineEdit, name: str) -> float:
        text = field.text().strip()
        if not text:
            self._mark_field_invalid(field)
            raise ValueError(f"{name} darf nicht leer sein.")
        if "," in text:
            self._mark_field_invalid(field)
            raise ValueError(f"{name} bitte mit '.' als Dezimaltrennzeichen angeben.")
        try:
            val = float(text)
            self._mark_field_valid(field)
            return val
        except ValueError:
            self._mark_field_invalid(field)
            raise ValueError(f"{name} muss eine Zahl sein.")

    def _import_measurements(self):
        self._set_error("")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Messwerte importieren",
            "",
            "Excel/CSV (*.xlsx *.xls *.csv);;Alle Dateien (*)",
        )
        if not file_path:
            return
        try:
            import pandas as pd

            if file_path.lower().endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            if df.shape[1] < 2:
                raise ValueError("Mindestens zwei Spalten erforderlich: Mr, C_mod (optional eta_min).")

            df = df.dropna()
            self.measurement_points = []
            for _, row in df.iterrows():
                mr = float(row.iloc[0])
                cmod = float(row.iloc[1])
                eta_val = float(row.iloc[2]) if df.shape[1] > 2 else None
                self.measurement_points.append({"Mr": mr, "C_mod": cmod, "eta_min": eta_val})

            self.update_plots()
        except Exception as exc:
            self._set_error(f"Import fehlgeschlagen: {exc}")

    def _set_error(self, msg: str):
        self.error_label.setText(msg)
        if not msg:
            for fld in self._fields:
                self._mark_field_valid(fld)

    def _mark_field_invalid(self, field: QLineEdit):
        field.setStyleSheet("border: 1px solid red;")

    def _mark_field_valid(self, field: QLineEdit):
        field.setStyleSheet("")

    def update_plots(self):
        try:
            mr_min = self._parse_float(self.mr_min_input, "M_r,min")
            mr_max = self._parse_float(self.mr_max_input, "M_r,max")
            if mr_max <= mr_min:
                raise ValueError("M_r,max muss größer als M_r,min sein.")
            points = int(self._parse_float(self.points_input, "Anzahl Punkte"))
            c_ref = self._parse_float(self.c_ref_input, "c_ref")
            scenario = self.scenario_combo.currentText()
        except ValueError as exc:
            self._set_error(str(exc))
            return

        self._set_error("")
        material = self.material_combo.currentText() or DEFAULT_MATERIAL
        M_r_values, C_mod_values, _ = generate_curves(mr_min, mr_max, points, scenario, material, c_ref)
        eta_min_values = [compute_eta_min_efsa(mr, scenario, c_ref) for mr in M_r_values]

        # Plot 1: C_mod
        self.cmod_figure.clear()
        ax1 = self.cmod_figure.add_subplot(111)
        ax1.plot(M_r_values, C_mod_values, color="#F06D1D", linewidth=2, label="C_mod")
        if self.measurement_points:
            xs = [p["Mr"] for p in self.measurement_points]
            ys = [p["C_mod"] for p in self.measurement_points]
            ax1.scatter(xs, ys, color="blue", s=30, label="Messwerte")
        ax1.set_xlabel("$M_{w}$ [g/mol]")
        ax1.set_ylabel("$C_{mod}$ [mg/kg]")
        ax1.set_title(f"EFSA Szenario {scenario} ({material}): $C_{{mod}}$")
        ax1.spines["left"].set_visible(True)
        ax1.spines["bottom"].set_visible(True)
        self.cmod_figure.subplots_adjust(left=0.14, bottom=0.14)
        ax1.grid(True, linestyle="--", alpha=0.5)
        if self.measurement_points:
            ax1.legend()
        self.cmod_canvas.draw()

        # Plot 2: eta_min
        self.eta_figure.clear()
        ax2 = self.eta_figure.add_subplot(111)
        ax2.plot(M_r_values, eta_min_values, color="#F06D1D", linewidth=2, label="eta_min")
        eta_points = [p for p in self.measurement_points if p.get("eta_min") is not None]
        if eta_points:
            xs = [p["Mr"] for p in eta_points]
            ys = [p["eta_min"] for p in eta_points]
            ax2.scatter(xs, ys, color="blue", s=30, label="Messwerte")
        ax2.set_xlabel("$M_{w}$ [g/mol]")
        ax2.set_ylabel("$\\eta_{min}$ [%]")
        ax2.set_title(f"EFSA Szenario {scenario} ({material}): $\\eta_{{min}}$")
        ax2.set_ylim(0, 110)
        ax2.spines["left"].set_visible(True)
        ax2.spines["bottom"].set_visible(True)
        self.eta_figure.subplots_adjust(left=0.14, bottom=0.14)
        ax2.grid(True, linestyle="--", alpha=0.5)
        if eta_points:
            ax2.legend()
        self.eta_canvas.draw()

    def _export_plots(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Plots exportieren (Basisname wählen)",
            "",
            "PNG (*.png);;PDF (*.pdf);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            self.cmod_figure.savefig(path.replace(".", "_cmod." + path.split(".")[-1]))
            self.eta_figure.savefig(path.replace(".", "_eta." + path.split(".")[-1]))
        except Exception as exc:
            self._set_error(f"Export fehlgeschlagen: {exc}")


class ParameterVariationTab(SingleLayerTab):
    """Abgeleitete Variante mit Fokus auf Parametervariationen."""

    def __init__(self):
        self.parameter_options = [
            "T_C",
            "M_r",
            "c_P0",
            "P_density",
            "F_density",
            "K_PF",
            "V_P",
            "V_F",
            "d_P",
            "d_F",
            "A_PF",
        ]
        self.parameter_units = {
            "T_C": "°C",
            "M_r": "g/mol",
            "c_P0": "mg/kg",
            "P_density": "g/cm³",
            "F_density": "g/cm³",
            "K_PF": "-",
            "V_P": "cm³",
            "V_F": "cm³",
            "d_P": "cm",
            "d_F": "cm",
            "A_PF": "dm²",
        }
        super().__init__()

    def create_grafical_setup(self):
        """Erstellt den Bereich für die grafische Darstellung samt Parametereingaben."""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setFixedHeight(220)
        self.graphics_view.setMaximumWidth(360)
        self.graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.rect_f.setRect(0, 0, self.default_d_F * 40, 100)
        self.rect_f.setBrush(self.color_init_F)
        self.graphics_scene.addItem(self.rect_f)

        self.rect_p.setRect(0, 0, self.default_d_P * 40, 100)
        self.rect_p.setBrush(self.color_init_P)
        self.graphics_scene.addItem(self.rect_p)

        graph_section = QVBoxLayout()
        graph_section.setSpacing(6)
        graph_section.setContentsMargins(0, 0, 0, 0)
        headline_label = QLabel("<b>Grafische Darstellung der Schichten</b>")
        headline_label.setAlignment(Qt.AlignLeft)
        graph_section.addWidget(headline_label)
        graph_section.addWidget(self.graphics_view)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addLayout(graph_section, 1)

        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(6)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        controls_label = QLabel("<b>Parametervariation</b>")
        controls_label.setAlignment(Qt.AlignLeft)
        controls_layout.addWidget(controls_label)

        self.parameter_dropdown = QComboBox()
        self.parameter_dropdown.addItems(self.parameter_options)
        self._apply_input_width(self.parameter_dropdown)
        controls_layout.addWidget(self._create_parameter_form_row("Parameter", self.parameter_dropdown))

        self.param_min_input = QLineEdit()
        self.param_max_input = QLineEdit()
        self.param_steps_input = QLineEdit("6")
        for field in (self.param_min_input, self.param_max_input, self.param_steps_input):
            field.setFixedHeight(22)
            field.setAlignment(Qt.AlignRight)
            field.setFixedWidth(self.input_width)

        min_widget, self.param_min_unit_label = self._create_range_row("Minimum", self.param_min_input)
        max_widget, self.param_max_unit_label = self._create_range_row("Maximum", self.param_max_input)
        steps_widget, _ = self._create_range_row("Anzahl Schritte", self.param_steps_input, with_unit=False)

        controls_layout.addWidget(min_widget)
        controls_layout.addWidget(max_widget)
        controls_layout.addWidget(steps_widget)
        controls_layout.addStretch()

        content_layout.addLayout(controls_layout, 0)
        layout.addLayout(content_layout)

        self.parameter_dropdown.currentTextChanged.connect(self._update_parameter_range_defaults)

        error_button_layout = QHBoxLayout()
        self.error_label.setFixedHeight(30)
        error_button_layout.addWidget(self.error_label, 1)

        self.start_button = QPushButton("Berechnung starten")
        self.start_button.setMinimumWidth(150)
        self.start_button.setFixedHeight(28)
        self.start_button.clicked.connect(self.start_parameter_variation)
        error_button_layout.addWidget(self.start_button, 0)

        layout.addLayout(error_button_layout)

        self._update_parameter_range_defaults()

        return layout

    def _create_parameter_form_row(self, label_text: str, widget: QWidget) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setMinimumWidth(90)
        row.addWidget(label)
        row.addWidget(widget)
        row.addStretch()
        container = QWidget()
        container.setLayout(row)
        return container

    def _create_range_row(self, label_text: str, widget: QLineEdit, with_unit: bool = True):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setMinimumWidth(90)
        unit_label = QLabel("" if not with_unit else "-")
        unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unit_label.setMinimumWidth(40)
        row.addWidget(label)
        row.addWidget(widget)
        if with_unit:
            row.addWidget(unit_label)
        row.addStretch(1)
        container = QWidget()
        container.setLayout(row)
        return container, unit_label if with_unit else None

    def _parameter_input_fields(self):
        return {
            "T_C": self.T_C_input,
            "M_r": self.M_r_input,
            "c_P0": self.c_P0_input,
            "P_density": self.P_density_input,
            "F_density": self.F_density_input,
            "K_PF": self.K_PF_input,
            "V_P": self.V_P_input,
            "V_F": self.V_F_input,
            "d_P": self.d_P_input,
            "d_F": self.d_F_input,
            "A_PF": self.A_PF_input,
        }

    def _update_parameter_range_defaults(self):
        parameter = self.parameter_dropdown.currentText()
        unit = self.parameter_units.get(parameter, "")
        if self.param_min_unit_label and unit:
            self.param_min_unit_label.setText(unit)
        if self.param_max_unit_label and unit:
            self.param_max_unit_label.setText(unit)

        source_field = self._parameter_input_fields().get(parameter)
        if source_field:
            current_value = source_field.text()
            if current_value:
                self.param_min_input.setText(current_value)
                self.param_max_input.setText(current_value)
                return
        self.param_min_input.clear()
        self.param_max_input.clear()

    def _parse_range_value(self, field: QLineEdit, label: str, as_int: bool = False):
        text = field.text().strip()
        if not text:
            self.mark_field_invalid(field)
            raise ValueError(f"{label} darf nicht leer sein.")
        if "," in text:
            self.mark_field_invalid(field)
            raise ValueError(f"{label} bitte '.' als Dezimaltrennzeichen verwenden.")
        try:
            value = int(text) if as_int else float(text)
            if value <= 0:
                raise ValueError
            self.mark_field_valid(field)
            return value
        except ValueError:
            self.mark_field_invalid(field)
            raise ValueError(f"{label} muss eine positive Zahl sein.")

    def start_parameter_variation(self):
        if not self.validate_inputs():
            self.show_error_message("Bitte korrigiere alle rot markierten Felder.")
            return

        parameter = self.parameter_dropdown.currentText()
        try:
            min_val = self._parse_range_value(self.param_min_input, "Minimum")
            max_val = self._parse_range_value(self.param_max_input, "Maximum")
            steps = self._parse_range_value(self.param_steps_input, "Anzahl Schritte", as_int=True)
        except ValueError as exc:
            self.show_error_message(str(exc))
            return

        if max_val <= min_val:
            self.show_error_message("Maximum muss größer als Minimum sein.")
            self.mark_field_invalid(self.param_max_input)
            return
        if steps < 2:
            self.show_error_message("Anzahl Schritte muss mindestens 2 sein.")
            self.mark_field_invalid(self.param_steps_input)
            return

        self.mark_field_valid(self.param_max_input)
        self.mark_field_valid(self.param_steps_input)

        param_range = list(np.linspace(min_val, max_val, steps))

        fixed_params = {
            "M_r": float(self.M_r_input.text()),
            "T_C": float(self.T_C_input.text()),
            "c_P0": float(self.c_P0_input.text()),
            "Material": self.material_dropdown.currentText(),
            "P_density": float(self.P_density_input.text()),
            "F_density": float(self.F_density_input.text()),
            "K_PF": float(self.K_PF_input.text()),
            "t_max": float(self.t_max_input.text()),
            "V_P": float(self.V_P_input.text()),
            "V_F": float(self.V_F_input.text()),
            "d_P": float(self.d_P_input.text()),
            "d_F": float(self.d_F_input.text()),
            "A_PF": float(self.A_PF_input.text()),
            "dt": float(self.dt_input.text()),
            "D_P_known": None if not self.D_P_known_input.text() else float(self.D_P_known_input.text()),
            "simulation_case": self.sim_case_dropdown.currentText(),
        }

        popup = ParameterVariationPopup(
            parameter,
            param_range,
            fixed_params,
            simulation_case=self.sim_case_dropdown.currentText(),
        )
        popup.show()
        self.variation_popup = popup


class SingleLayerSuiteTab(QWidget):
    """
    Container-Tab für Single-Layer-Funktionen: Migration, Curve-Fitting, Parametervariation.
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        from curve_fitting_gui import CurveFittingTab  # Lazy import, um Zyklen zu vermeiden

        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(SingleLayerTab(), "Migrationsberechnung")
        self.sub_tabs.addTab(ParameterVariationTab(), "Parametervariation")
        self.sub_tabs.addTab(CurveFittingTab(), "Curve Fitting")
        self.sub_tabs.addTab(EFSAExtendedTab(), "EFSA")

        layout.addWidget(self.sub_tabs)
