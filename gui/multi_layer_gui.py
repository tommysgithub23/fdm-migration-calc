from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QFormLayout, QLineEdit, QHBoxLayout, QGraphicsView, QGraphicsScene, QSizePolicy, QSpacerItem, QComboBox, QTableWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from ml_model_functions import Layer, run_simulation, plot_results, plot_migrated_mass_over_time, calculate_migrated_mass_over_time

class MultiLayerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]

        # Hauptlayout
        self.main_layout = QVBoxLayout(self)

        # Überschriften
        input_label = QLabel("<b>Eingabe</b>")
        table_label = QLabel("<b>Schichten-Tabelle</b>")
        graphics_label = QLabel("<b>Grafische Darstellung der Schichten</b>")

        # Layout für Eingabebereich und Tabelle
        self.top_layout = QGridLayout()
        self.main_layout.addLayout(self.top_layout)

        # Eingabebereich (links)
        self.input_layout = QVBoxLayout()
        self.T_C_input = QLineEdit("40")
        self.M_r_input = QLineEdit("531")
        self.t_max_input = QLineEdit("10")
        self.d_nx_input = QLineEdit("0.02")

        # Validierung verbinden
        for fld in (self.T_C_input, self.M_r_input, self.t_max_input, self.d_nx_input):
            fld.textChanged.connect(lambda _, f=fld: self.validate_field(f))

        # Signale verbinden
        self.d_nx_input.textChanged.connect(self.update_all_nx_from_ratio)
        self.d_nx_input.textChanged.connect(lambda _: self.validate_field(self.d_nx_input))

        # Nutze addWidget und setze die Elemente linksbündig
        self.input_layout.addWidget(self._create_labeled_row("T<sub>C</sub>", "°C", self.T_C_input))
        self.input_layout.addWidget(self._create_labeled_row("M<sub>r</sub>", "g/mol", self.M_r_input))
        self.input_layout.addWidget(self._create_labeled_row("t<sub>max</sub>", "Tage", self.t_max_input))
        self.input_layout.addWidget(self._create_labeled_row("d/n<sub>x</sub>", "cm", self.d_nx_input))
        self.input_layout.setAlignment(Qt.AlignLeft)  # Links-Ausrichtung für den gesamten Eingabebereich

        # --- Schichtentabelle (rechts) ---
        self.layer_table = QTableWidget(0, 5)
        self.layer_table.setHorizontalHeaderLabels(["Material", "d (cm)", "nₓ", "Kₓ", "C₀ (mg/kg)"])
        self.layer_table.cellChanged.connect(self.update_nx_on_d_change)
        self.layer_table.cellChanged.connect(self._on_table_cell_changed)

        self.main_layout.addWidget(self.layer_table)

        # Buttons unter der Tabelle
        self.button_layout = QHBoxLayout()
        self.add_layer_button = QPushButton()
        self.add_layer_button.setIcon(QIcon.fromTheme("list-add"))
        self.add_layer_button.setFixedSize(30, 30)
        self.add_layer_button.setIconSize(self.add_layer_button.size())
        self.add_layer_button.clicked.connect(self.add_layer)

        self.remove_layer_button = QPushButton()
        self.remove_layer_button.setIcon(QIcon.fromTheme("list-remove"))
        self.remove_layer_button.setFixedSize(30, 30)
        self.remove_layer_button.setIconSize(self.remove_layer_button.size())
        self.remove_layer_button.clicked.connect(self.remove_layer)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.add_layer_button)
        self.button_layout.addWidget(self.remove_layer_button)

        # --- Top Layout: Eingaben und Tabelle ---
        self.top_layout.addWidget(input_label, 0, 0, Qt.AlignLeft)
        self.top_layout.addLayout(self.input_layout, 1, 0, Qt.AlignTop | Qt.AlignLeft)
        self.top_layout.addWidget(table_label, 0, 1, Qt.AlignLeft)
        self.top_layout.addWidget(self.layer_table, 1, 1)
        self.top_layout.addLayout(self.button_layout, 2, 1, Qt.AlignRight)

        # Abstände und Margins anpassen
        self.top_layout.setColumnStretch(0, 1)  # Eingabe kleiner halten
        self.top_layout.setColumnStretch(1, 2)  # Tabelle breiter machen
        self.top_layout.setContentsMargins(10, 10, 10, 10)
        self.top_layout.setHorizontalSpacing(20)
        self.top_layout.setVerticalSpacing(10)

        # --- Grafische Darstellung (unten) ---
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)

        self.main_layout.addWidget(graphics_label)
        self.main_layout.addWidget(self.graphics_view)
        self.main_layout.addStretch()

        # !Farben noch entsprechend anpassen
        self.material_colors = {
            "LDPE": Qt.green,
            "LLDPE": Qt.darkGreen,
            "HDPE": Qt.cyan,
            "PP": Qt.yellow,
            "PET": Qt.magenta,
            "PS": Qt.gray,
            "PEN": Qt.darkCyan,
            "HIPS": Qt.darkBlue,
            "Kontaktphase": Qt.lightGray
        }

        # Start-Button
        self.start_button = QPushButton("Simulation starten")
        self.main_layout.addWidget(self.start_button)
        self.main_layout.setAlignment(self.start_button, Qt.AlignCenter)

        self.start_button.clicked.connect(self.start_calculation)

        # Fehler-Label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.main_layout.addWidget(self.error_label)

        # Tabelle mit zwei Spalten als Start vorbereiten
        self.add_contact_phase()
        self.add_layer()

    def _create_labeled_row(self, label_text, unit_text, input_field):
        """Erstellt ein QWidget mit einem QHBoxLayout, das Label, Eingabefeld und Einheit enthält."""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(5)  # Abstand zwischen den Widgets
        row_layout.setContentsMargins(0, 0, 0, 0)  # Entferne zusätzliche Margins

        # Label für die Beschreibung
        label = QLabel(f"<html>{label_text}</html>")
        label.setFixedWidth(40)  # Feste Breite für Label für gleichmäßige Ausrichtung
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Rechts ausgerichtet, vertikal zentriert

        # Eingabefeld
        input_field.setFixedWidth(70)  # Einheitliche Breite für die Eingabefelder
        input_field.setFixedHeight(25)  # Einheitliche Höhe für die Eingabefelder
        input_field.setAlignment(Qt.AlignRight)  # Text im Eingabefeld rechts ausrichten

        # Label für die Einheit
        unit_label = QLabel(unit_text)
        unit_label.setFixedWidth(50)  # Feste Breite für die Einheit
        unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Links ausgerichtet, vertikal zentriert

        # Füge Widgets dem Layout hinzu
        row_layout.addWidget(label)
        row_layout.addWidget(input_field)
        row_layout.addWidget(unit_label)

        # Verpacke das Layout in ein Widget
        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        return row_widget

    def is_valid_number(self, value: str) -> bool:
        txt = value.strip().replace(',', '.')
        if not txt:
            return False
        try:
            float(txt)
            return True
        except ValueError:
            return False

    def mark_field_invalid(self, field):
        field.setStyleSheet("border:1px solid red;")

    def mark_field_valid(self, field):
        field.setStyleSheet("")

    def validate_field(self, field: QLineEdit):
        if self.is_valid_number(field.text()):
            self.mark_field_valid(field)
            self.error_label.setText("")
        else:
            self.mark_field_invalid(field)
            self.show_error_message("Bitte korrigiere alle rot markierten Felder.")

    def _on_table_cell_changed(self, row: int, col: int):
        # 1) Ratio-Logik wie bisher
        self.update_nx_on_d_change(row, col)

        # 2) Validierung für numerische Spalten:
        if col in (1, 2, 3, 4):
            item = self.layer_table.item(row, col)
            if item:
                txt = item.text().strip().replace(',', '.')
                try:
                    float(txt)
                    # gültig -> schwarzen Hintergrund
                    self.layer_table.blockSignals(True)
                    item.setBackground(Qt.black)
                    self.layer_table.blockSignals(False)
                    self.error_label.setText("")
                except ValueError:
                    # ungültig - >roten Hintergrund
                    self.layer_table.blockSignals(True)
                    item.setBackground(QColor("#FF0000"))
                    self.layer_table.blockSignals(False)
                    self.show_error_message("Ungültige Zahl in Tabelle – bitte korrigieren.")

    def show_error_message(self, msg: str):
        self.error_label.setText(msg)

    def add_layer(self):
        insert_at = self.layer_table.rowCount() - 1
        self.layer_table.insertRow(insert_at)

        # --- Spalte 0: Material-Dropdown ---
        material_dropdown = QComboBox()
        material_dropdown.addItems(self.material_list)
        material_dropdown.currentTextChanged.connect(self.update_graphics)
        self.layer_table.setCellWidget(insert_at, 0, material_dropdown)

        # --- Spalten 1 bis 4: normale Eingabefelder ---
        default_values = ["0.0", "10", "1.0", "0.0"]
        for col, value in enumerate(default_values, start=1):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            self.layer_table.setItem(insert_at, col, item)

        self.update_graphics()


    
    def add_contact_phase(self):
        # Die fl. Kontaktphase ist immer die unterste Schicht ohne Dropdown
        row_count = self.layer_table.rowCount()
        self.layer_table.insertRow(row_count)

        contact_material = QTableWidgetItem("Kontaktphase")
        contact_material.setTextAlignment(Qt.AlignCenter)
        contact_material.setFlags(contact_material.flags() & ~Qt.ItemIsEditable)
        self.layer_table.setItem(row_count, 0, contact_material)

        default_values = ["0.0", "10", "1.0", "0.0"]
        for col, value in enumerate(default_values, start=1):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            self.layer_table.setItem(row_count, col, item)

    def get_material_from_row(self, row):
        widget = self.layer_table.cellWidget(row, 0)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        item = self.layer_table.item(row, 0)
        return item.text() if item else None
    
    def update_nx_on_d_change(self, row, column):
        if column != 1:
            return  # Nur reagieren, wenn Spalte d(cm) geändert wird

        try:
            ratio = float(self.d_nx_input.text())
            d_item = self.layer_table.item(row, 1)
            if d_item:
                d_value = float(d_item.text())
                n_x = max(1, round(d_value / ratio))
                self.layer_table.blockSignals(True)
                # Wenn kein nₓ-Eintrag vorhanden ist, erstelle ihn
                if not self.layer_table.item(row, 2):
                    n_item = QTableWidgetItem()
                    n_item.setTextAlignment(Qt.AlignCenter)
                    self.layer_table.setItem(row, 2, n_item)
                self.layer_table.item(row, 2).setText(str(n_x))
                self.layer_table.blockSignals(False)
        except (ValueError, AttributeError):
            pass

        self.update_graphics()


    def update_all_nx_from_ratio(self):
        try:
            ratio = float(self.d_nx_input.text())
            for row in range(self.layer_table.rowCount()):
                d_item = self.layer_table.item(row, 1)
                if d_item:
                    d_value = float(d_item.text())
                    n_x = max(1, round(d_value / ratio))
                    self.layer_table.blockSignals(True)
                    if not self.layer_table.item(row, 2):
                        n_item = QTableWidgetItem()
                        n_item.setTextAlignment(Qt.AlignCenter)
                        self.layer_table.setItem(row, 2, n_item)
                    self.layer_table.item(row, 2).setText(str(n_x))
                    self.layer_table.blockSignals(False)
        except ValueError:
            pass
        self.update_graphics()


    def remove_layer(self):
        row_count = self.layer_table.rowCount()
        if row_count > 1:
            self.layer_table.removeRow(row_count - 2)  # Entferne oberste Nutzschicht, nicht Kontaktphase
        self.update_graphics()

    def update_graphics(self):
        self.graphics_scene.clear()
        x_offset = 0
        height = 100
        scaling = 40  # cm -> px

        for row in range(self.layer_table.rowCount()):
            d_item = self.layer_table.item(row, 1)
            d = 0
            if d_item:
                try:
                    d = float(d_item.text())
                except ValueError:
                    continue

            # Breite aus d
            width = d * scaling

            # Material auslesen
            material = self.get_material_from_row(row)
            color = self.material_colors.get(material, Qt.red)

            rect = self.graphics_scene.addRect(x_offset, 0, width, height)
            rect.setBrush(color)
            rect.setToolTip(f"{material}: {d} cm")
            x_offset += width

    def start_calculation(self):
        """Liest alle Eingaben aus, baut die Layer-Liste, führt die Simulation durch und zeigt das Ergebnis."""
        # 1) Globale Felder validieren
        for fld in (self.T_C_input, self.M_r_input, self.t_max_input, self.d_nx_input):
            if not self.is_valid_number(fld.text()):
                self.validate_field(fld)
                return

        # 2) Tabelleneinträge validieren
        valid = True
        for row in range(self.layer_table.rowCount()):
            for col in (1, 2, 3, 4):  # d, nₓ, Kₓ, C₀
                item = self.layer_table.item(row, col)
                if item is None or not self.is_valid_number(item.text()):
                    self.layer_table.blockSignals(True)
                    if item: item.setBackground(QColor("#FFCCCC"))
                    self.layer_table.blockSignals(False)
                    valid = False
        if not valid:
            self.show_error_message("Bitte korrigiere alle rot markierten Felder.")
            return

        # 3) Parameter auslesen
        M_r  = float(self.M_r_input.text().replace(',', '.'))
        T_C  = float(self.T_C_input.text().replace(',', '.'))
        # t_max wird in Tagen eingegeben → in Sekunden umrechnen
        t_max_days = float(self.t_max_input.text().replace(',', '.'))
        t_max = t_max_days * 24 * 3600
        # Verwende festen Zeitschritt (kann später als Eingabe ergänzt werden)
        dt = 1.0  

        # 4) Layer-Liste bauen
        layers = []
        for row in range(self.layer_table.rowCount()):
            material = self.get_material_from_row(row)
            d       = float(self.layer_table.item(row, 1).text().replace(',', '.'))
            nx      = int(float(self.layer_table.item(row, 2).text().replace(',', '.')))
            K_val   = float(self.layer_table.item(row, 3).text().replace(',', '.'))
            C_init  = float(self.layer_table.item(row, 4).text().replace(',', '.'))
            layer = Layer(material, d, nx, K_val, C_init)       # :contentReference[oaicite:3]{index=3}
            layer.set_diffusion_coefficient(M_r, T_C)            # :contentReference[oaicite:4]{index=4}
            layers.append(layer)

        C_values, C_init, total_masses, x, partitioning = run_simulation(layers, t_max, dt)  # :contentReference[oaicite:5]{index=5}&#8203;:contentReference[oaicite:6]{index=6}

        plot_results(C_values, C_init, x, layers, dt)                      # :contentReference[oaicite:7]{index=7}&#8203;:contentReference[oaicite:8]{index=8}

        migrated_mass, time_points = calculate_migrated_mass_over_time(
            C_values, x, layers, dt, calc_interval=1
        )

        plot_migrated_mass_over_time(migrated_mass, time_points, save_path=None)
