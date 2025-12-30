import csv

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QLineEdit, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QSizePolicy, QComboBox, QApplication, QDialog, QMenu, QTabWidget,
    QFileDialog, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QPalette
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from ml_model_functions import (
    Layer,
    run_simulation,
    plot_results,
    plot_migrated_mass_over_time,
    calculate_migrated_mass_over_time,
    calculate_migrated_mass_over_time_by_layer,
    plot_migrated_mass_over_time_by_layer,
)
from tooltip_helper import DelayedToolTipHelper


class MultiLayerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]
        self.tooltip_helper = DelayedToolTipHelper(parent=self)
        self.label_width = 70
        self.input_width = 90
        self.unit_width = 20
        self._last_results = {}
        self.results_dialogs = []

        # Hauptlayout
        self.main_layout = QVBoxLayout(self)

        # Gemeinsames zweispaltiges Layout (wie im Single-Layer-Tab)
        self.split_layout = QHBoxLayout()
        self.split_layout.setSpacing(20)
        self.split_layout.setContentsMargins(0, 12, 0, 0)
        self.main_layout.addLayout(self.split_layout)

        # Eingabebereich (linke Spalte)
        self.input_layout = QVBoxLayout()
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.T_C_input = QLineEdit("25")
        self.M_r_input = QLineEdit("136")
        self.t_max_input = QLineEdit("10")
        self.dt_input = QLineEdit("1000")
        self.d_nx_input = QLineEdit("0.02")
        self.threshold_input = QLineEdit("1e-5")
        self.threshold_checkbox = QCheckBox("")
        self.threshold_input.setEnabled(False)
        self.threshold_input.setFixedHeight(25)
        self.threshold_input.setFixedWidth(self.input_width)
        self.threshold_input.setAlignment(Qt.AlignRight)
        self.sim_case_dropdown = QComboBox()
        self.sim_case_dropdown.addItems(["worst", "best"])
        self.tooltip_helper.register(self.T_C_input, "Temperatur der Simulation in °C.")
        self.tooltip_helper.register(self.M_r_input, "Relative Molekülmasse des Migranten in g/mol.")
        self.tooltip_helper.register(self.t_max_input, "Gesamtdauer der Simulation in Tagen (wird in Sekunden umgerechnet).")
        self.tooltip_helper.register(self.dt_input, "Zeitschrittgröße in Sekunden.")
        self.tooltip_helper.register(self.d_nx_input, "Verhältnis von Schichtdicke zu räumlicher Diskretisierung d/nₓ in cm.")
        self.tooltip_helper.register(
            self.sim_case_dropdown,
            "Bestimmt, ob mit Worst-Case- oder Best-Case-Annahmen gerechnet wird (Diffusionskoeffizient nach Piringer).",
        )
        self.tooltip_helper.register(self.threshold_checkbox, "Grenzwertlinie im Migrationsplot aktivieren.")
        self.tooltip_helper.register(self.threshold_input, "Grenzwert für die Migrationsmenge in mg/dm².")

        # Validierung verbinden
        for fld in (self.T_C_input, self.M_r_input, self.t_max_input, self.dt_input, self.d_nx_input):
            fld.textChanged.connect(lambda _, f=fld: self.validate_field(f))

        # Signale verbinden
        self.d_nx_input.textChanged.connect(self.update_all_nx_from_ratio)
        self.d_nx_input.textChanged.connect(lambda _: self.validate_field(self.d_nx_input))
        self.threshold_checkbox.toggled.connect(self.threshold_input.setEnabled)
        self.threshold_checkbox.toggled.connect(lambda _: self.validate_inputs())
        self.threshold_input.textChanged.connect(
            lambda: self.validate_field(self.threshold_input)
            if self.threshold_checkbox.isChecked()
            else None
        )

        # Nutze addWidget und setze die Elemente linksbündig
        self.input_layout.addWidget(self._create_labeled_row("T<sub>C</sub>", "°C", self.T_C_input))
        self.input_layout.addWidget(self._create_labeled_row("M<sub>r</sub>", "g/mol", self.M_r_input))
        self.input_layout.addWidget(self._create_labeled_row("t<sub>max</sub>", "Tage", self.t_max_input))
        self.input_layout.addWidget(self._create_labeled_row("Δt", "s", self.dt_input))
        self.input_layout.addWidget(self._create_labeled_row("d/n<sub>x</sub>", "cm", self.d_nx_input))
        threshold_row = QHBoxLayout()
        threshold_row.setSpacing(6)
        threshold_row.setContentsMargins(0, 0, 0, 0)
        threshold_label = QLabel("<html>Grenzwert</html>")
        threshold_label.setMinimumWidth(self.label_width)
        threshold_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        threshold_unit = QLabel("mg/dm²")
        threshold_unit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        threshold_unit.setMinimumWidth(self.unit_width)
        threshold_row.addWidget(threshold_label)
        threshold_row.addWidget(self.threshold_input)
        threshold_row.addWidget(threshold_unit)
        threshold_row.addWidget(self.threshold_checkbox)
        threshold_row.addStretch()
        threshold_container = QWidget()
        threshold_container.setLayout(threshold_row)
        self.input_layout.addWidget(threshold_container)
        self.input_layout.setAlignment(Qt.AlignLeft)  # Links-Ausrichtung für den gesamten Eingabebereich
        self.input_layout.addWidget(self._create_labeled_row("Simulation Case", "", self.sim_case_dropdown))
        self.input_layout.setSpacing(6)

        left_column = QVBoxLayout()
        left_column.setSpacing(6)
        left_column.setContentsMargins(0, 0, 0, 0)
        input_label = QLabel("<b>Physikalische/chemische Größen</b>")
        input_label.setAlignment(Qt.AlignLeft)
        left_column.addWidget(input_label)
        left_column.addLayout(self.input_layout)
        left_column.addStretch()

        # --- Schichtentabelle (rechte Spalte, oberer Bereich) ---
        self.layer_table = QTableWidget(0, 6)
        headers = ["Material", "d (cm)", "nₓ", "Kₓ", "c₀ (mg/kg)", "ρ (g/cm³)"]
        self.layer_table.setHorizontalHeaderLabels(headers)
        self.column_tooltips = {
            0: "Materialtyp der Schicht.",
            1: "Schichtdicke d in Zentimetern.",
            2: "Anzahl der Diskretisierungselemente nₓ.",
            3: "Verteilungskoeffizient Kₓ zur nächsten Schicht.",
            4: "Anfangskonzentration c₀ der Schicht in mg/kg.",
            5: "Dichte ρ der Schicht in g/cm³."
        }
        for col, text in self.column_tooltips.items():
            header_item = self.layer_table.horizontalHeaderItem(col)
            if header_item:
                header_item.setToolTip(text)
        header = self.layer_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        self.layer_table.setColumnWidth(0, 100)
        self.layer_table.setColumnWidth(1, 90)
        self.layer_table.setColumnWidth(2, 90)
        self.layer_table.setColumnWidth(3, 90)
        self.layer_table.setColumnWidth(4, 90)
        self.layer_table.setColumnWidth(5, 90)
        self.layer_table.setMinimumHeight(130)
        self.tooltip_helper.register(
            self.layer_table,
            "Tabelle der Schichten: Doppelklick auf eine Zelle, um Werte zu bearbeiten."
        )
        self.layer_table.cellChanged.connect(self.update_nx_on_d_change)
        self.layer_table.cellChanged.connect(self._on_table_cell_changed)

        # Tabellen-Interaktionen: Enter in letzter Zeile fügt neue Schicht hinzu,
        # Kontextmenü erlaubt das Entfernen einer Zeile (Kontaktphase bleibt geschützt).
        self.layer_table.installEventFilter(self)
        self.layer_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layer_table.customContextMenuRequested.connect(self._show_layer_context_menu)

        table_section = QVBoxLayout()
        table_section.setSpacing(6)
        table_section.setContentsMargins(0, 0, 0, 0)
        table_label = QLabel("<b>Schichtaufbau</b>")
        table_label.setAlignment(Qt.AlignLeft)
        table_section.addWidget(table_label)
        table_section.addWidget(self.layer_table)
        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        add_btn = QPushButton("Layer hinzufügen")
        add_btn.setProperty("appStyle", False)
        add_btn.clicked.connect(lambda: self.add_layer(select_new_row=True))
        remove_btn = QPushButton("Layer entfernen")
        remove_btn.setProperty("appStyle", False)
        remove_btn.clicked.connect(self.remove_layer)
        button_row.addWidget(add_btn)
        button_row.addWidget(remove_btn)
        button_row.addStretch()
        table_section.addLayout(button_row)

        # --- Grafische Darstellung (rechte Spalte, unterer Bereich) ---
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setFixedHeight(160)
        self.graphics_view.setMaximumWidth(250)
        self.graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        graphics_section = QVBoxLayout()
        graphics_section.setSpacing(6)
        graphics_section.setContentsMargins(0, 0, 0, 0)
        graphics_label = QLabel("<b>Grafische Darstellung</b>")
        graphics_label.setAlignment(Qt.AlignLeft)
        graphics_section.addWidget(graphics_label)
        graphics_section.addWidget(self.graphics_view)

        # !Farben noch entsprechend anpassen
        self.material_colors = {
            "LDPE": QColor("#f16d1d"),
            "LLDPE": QColor("#f16d1d"),
            "HDPE": QColor("#32c864"),
            "PP": QColor("#c832ee"),
            "PET": QColor("#646464"),
            "PS": QColor("#8c564b"),
            "PEN": Qt.darkCyan,
            "HIPS": Qt.darkBlue,
            "Kontaktphase": QColor("#64e6df"),
        }

        
        # Start-Button
        self.start_button = QPushButton("Berechnung starten")
        self.start_button.setFixedSize(150, 28)
        self.start_button.setProperty("appStyle", True)
        self.tooltip_helper.register(self.start_button, "Führt die Simulation mit den eingegebenen Schichten aus.")

        self.start_button.pressed.connect(self._finalize_pending_table_edits)
        self.start_button.clicked.connect(self.start_calculation)

        # Fehler-Label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self.error_label, 1)
        controls_layout.addWidget(self.start_button, 0, Qt.AlignRight)

        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.addLayout(table_section)
        right_column.addLayout(graphics_section)
        right_column.addLayout(controls_layout)

        self.split_layout.addLayout(left_column, 1)
        self.split_layout.addLayout(right_column, 2)

        # Tabelle mit zwei Spalten als Start vorbereiten
        self.add_contact_phase()
        self.add_layer()
        self.update_all_nx_from_ratio()

    def eventFilter(self, obj, event):
        if obj is self.layer_table and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                # In vorletzter Zeile (oberste Nutzschicht) -> neue Schicht anlegen
                if self.layer_table.rowCount() >= 2 and self.layer_table.currentRow() == self.layer_table.rowCount() - 2:
                    self.add_layer(select_new_row=True)
                    return True
        return super().eventFilter(obj, event)

    def _create_labeled_row(self, label_text, unit_text, input_field):
        """Erstellt ein QWidget mit einem QHBoxLayout, das Label, Eingabefeld und Einheit enthält."""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(6)  # Abstand zwischen den Widgets
        row_layout.setContentsMargins(0, 0, 0, 0)  # Entferne zusätzliche Margins

        # Label für die Beschreibung
        label = QLabel(f"<html>{label_text}</html>")
        label.setMinimumWidth(self.label_width)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Eingabefeld
        if isinstance(input_field, QLineEdit):
            input_field.setFixedWidth(self.input_width)
            input_field.setFixedHeight(25)  # Einheitliche Höhe für die Eingabefelder
            input_field.setAlignment(Qt.AlignRight)  # Text im Eingabefeld rechts ausrichten
        elif isinstance(input_field, QComboBox):
            input_field.setFixedHeight(25)
            input_field.setFixedWidth(self.input_width)
            input_field.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)

        # Label für die Einheit
        unit_label = QLabel(unit_text)
        unit_label.setMinimumWidth(self.unit_width)
        unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Links ausgerichtet, vertikal zentriert
        unit_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Füge Widgets dem Layout hinzu
        row_layout.addWidget(label)
        row_layout.addWidget(input_field)
        row_layout.addWidget(unit_label)
        row_layout.addStretch()

        # Verpacke das Layout in ein Widget
        row_widget = QWidget()
        row_widget.setLayout(row_layout)

        return row_widget

    def is_valid_number(self, value: str) -> bool:
        txt = value.strip()
        if not txt:
            return False
        if "," in txt:
            self.show_error_message("Bitte '.' als Dezimaltrennzeichen verwenden.")
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

    def mark_table_cell_invalid(self, row: int, col: int):
        item = self.layer_table.item(row, col)
        if item is None:
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.layer_table.setItem(row, col, item)
        item.setBackground(QColor("#FFCCCC"))

    def mark_table_cell_valid(self, row: int, col: int):
        item = self.layer_table.item(row, col)
        if item:
            base_color = self.layer_table.palette().color(QPalette.Base)
            item.setBackground(base_color)

    def validate_inputs(self) -> bool:
        """Prüft alle Eingaben und markiert ungültige Felder/Table-Cells."""
        is_valid = True

        scalar_fields = (
            self.T_C_input,
            self.M_r_input,
            self.t_max_input,
            self.dt_input,
            self.d_nx_input,
        )
        for field in scalar_fields:
            if self.is_valid_number(field.text()):
                self.mark_field_valid(field)
            else:
                self.mark_field_invalid(field)
                is_valid = False

        if self.threshold_checkbox.isChecked():
            if self.is_valid_number(self.threshold_input.text()):
                try:
                    if float(self.threshold_input.text()) <= 0:
                        raise ValueError
                    self.mark_field_valid(self.threshold_input)
                except ValueError:
                    self.mark_field_invalid(self.threshold_input)
                    is_valid = False
            else:
                self.mark_field_invalid(self.threshold_input)
                is_valid = False
        else:
            self.mark_field_valid(self.threshold_input)

        for row in range(self.layer_table.rowCount()):
            for col in (1, 2, 3, 4, 5):
                if not self._validate_table_value(row, col):
                    is_valid = False

        if is_valid:
            self.error_label.setText("")

        return is_valid

    def _validate_table_value(self, row: int, col: int) -> bool:
        item = self.layer_table.item(row, col)
        text = item.text().strip() if item and item.text() else ""
        if not self.is_valid_number(text):
            self.mark_table_cell_invalid(row, col)
            return False
        self.mark_table_cell_valid(row, col)
        return True

    def validate_field(self, field: QLineEdit):
        if self.is_valid_number(field.text()):
            self.mark_field_valid(field)
        else:
            self.mark_field_invalid(field)

    def _on_table_cell_changed(self, row: int, col: int):
        # 1) Ratio-Logik wie bisher
        self.update_nx_on_d_change(row, col)

        # 2) Validierung für numerische Spalten:
        if col in (1, 2, 3, 4, 5):
            self._validate_table_value(row, col)

    def show_error_message(self, msg: str):
        self.error_label.setText(msg)

    def add_layer(self, select_new_row: bool = False):
        insert_at = self.layer_table.rowCount() - 1
        self.layer_table.insertRow(insert_at)

        # --- Spalte 0: Material-Dropdown ---
        material_dropdown = QComboBox()
        material_dropdown.addItems(self.material_list)
        material_dropdown.currentTextChanged.connect(self.update_graphics)
        self.tooltip_helper.register(material_dropdown, "Materialwahl für diese Schicht.")
        self.layer_table.setCellWidget(insert_at, 0, material_dropdown)

        # --- Spalten 1 bis 4: normale Eingabefelder ---
        default_values = ["0.2", "10", "1.0", "0.0", "1.0"]
        for col, value in enumerate(default_values, start=1):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            tooltip = self.column_tooltips.get(col)
            if tooltip:
                item.setToolTip(tooltip)
            self.layer_table.setItem(insert_at, col, item)

        self.update_graphics()

        if select_new_row:
            self.layer_table.setCurrentCell(insert_at, 1)
            item = self.layer_table.item(insert_at, 1)
            if item:
                self.layer_table.editItem(item)

    def remove_layer(self):
        # Löscht ausgewählte Zeile oder oberste Nutzschicht; Kontaktphase (letzte Zeile) bleibt bestehen.
        row_count = self.layer_table.rowCount()
        if row_count <= 1:
            return
        selected_rows = {idx.row() for idx in self.layer_table.selectionModel().selectedIndexes()}
        if not selected_rows:
            target_row = row_count - 2
        else:
            target_row = min(selected_rows)
        if target_row >= row_count - 1:  # Kontaktphase geschützt
            return
        self.layer_table.removeRow(target_row)
        self.update_graphics()

    def _show_layer_context_menu(self, pos):
        index = self.layer_table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        menu = QMenu(self)
        remove_action = menu.addAction("Zelle entfernen")
        # Kontaktphase (letzte Zeile) nicht löschbar
        if row == self.layer_table.rowCount() - 1:
            remove_action.setEnabled(False)

        action = menu.exec(self.layer_table.mapToGlobal(pos))
        if action == remove_action and remove_action.isEnabled():
            self.layer_table.removeRow(row)
            self.update_graphics()

    def _finalize_pending_table_edits(self):
        """
        Stellt sicher, dass offene Editor-Widgets (z. B. in der Tabelle) ihren
        aktuellen Wert in das QTableWidgetItem übernehmen, bevor die Berechnung startet.
        Qt commitet Werte häufig erst nach dem Durchlauf des Event-Loops; durch das
        Erzwingen eines kurzen Event-Flushes und das manuelle Setzen verhindern wir,
        dass frische Eingaben verloren gehen, wenn der Nutzer direkt den Start-Button klickt.
        """
        QApplication.processEvents()
        current_row = self.layer_table.currentRow()
        current_col = self.layer_table.currentColumn()
        if current_row < 0 or current_col < 0:
            return

        # Suche nach sichtbaren Editor-Widgets (z. B. QLineEdit) innerhalb des Tables.
        for editor in self.layer_table.findChildren(QLineEdit):
            if not editor.isVisible():
                continue

            item = self.layer_table.item(current_row, current_col)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                self.layer_table.setItem(current_row, current_col, item)

            new_value = editor.text()
            if item.text() != new_value:
                item.setText(new_value)
            break

    
    def add_contact_phase(self):
        # Die fl. Kontaktphase ist immer die unterste Schicht ohne Dropdown
        row_count = self.layer_table.rowCount()
        self.layer_table.insertRow(row_count)

        contact_material = QTableWidgetItem("Kontaktphase")
        contact_material.setTextAlignment(Qt.AlignCenter)
        contact_material.setFlags(contact_material.flags() & ~Qt.ItemIsEditable)
        contact_material.setToolTip(self.column_tooltips.get(0, ""))
        self.layer_table.setItem(row_count, 0, contact_material)

        default_values = ["2.0", "10", "1.0", "0.0", "0.9"]
        for col, value in enumerate(default_values, start=1):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            tooltip = self.column_tooltips.get(col)
            if tooltip:
                item.setToolTip(tooltip)
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
        self._finalize_pending_table_edits()

        if not self.validate_inputs():
            self.show_error_message("Bitte korrigiere alle rot markierten Felder.")
            return

        # 3) Parameter auslesen
        M_r  = float(self.M_r_input.text())
        T_C  = float(self.T_C_input.text())
        simulation_case = self.sim_case_dropdown.currentText()
        # t_max wird in Tagen eingegeben → in Sekunden umrechnen
        t_max_days = float(self.t_max_input.text())
        t_max = t_max_days * 24 * 3600
        dt = float(self.dt_input.text())

        # 4) Layer-Liste bauen
        layers = []
        for row in range(self.layer_table.rowCount()):
            material = self.get_material_from_row(row)
            d       = float(self.layer_table.item(row, 1).text())
            nx      = int(float(self.layer_table.item(row, 2).text()))
            K_val   = float(self.layer_table.item(row, 3).text())
            C_init  = float(self.layer_table.item(row, 4).text())
            density = float(self.layer_table.item(row, 5).text())
            layer = Layer(material, d, nx, K_val, C_init, density=density)       # :contentReference[oaicite:3]{index=3}
            layer.set_diffusion_coefficient(M_r, T_C, simulation_case=simulation_case)  # :contentReference[oaicite:4]{index=4}
            layers.append(layer)

        C_values, C_init, total_masses, x, partitioning = run_simulation(layers, t_max, dt)  # :contentReference[oaicite:5]{index=5}&#8203;:contentReference[oaicite:6]{index=6}

        concentration_fig = plot_results(C_values, C_init, x, layers, dt, show=False)

        migrated_mass, time_points = calculate_migrated_mass_over_time(
            C_values, x, layers, dt, calc_interval=1
        )
        migrated_mass_by_layer, layer_time_points = calculate_migrated_mass_over_time_by_layer(
            C_values, x, layers, dt, calc_interval=1
        )
        threshold = None
        if self.threshold_checkbox.isChecked():
            try:
                threshold = float(self.threshold_input.text())
            except ValueError:
                threshold = None

        migration_fig = plot_migrated_mass_over_time(
            migrated_mass,
            time_points,
            save_path=None,
            show=False,
            threshold=threshold,
        )
        migration_by_layer_fig = plot_migrated_mass_over_time_by_layer(
            migrated_mass_by_layer,
            layer_time_points,
            layers,
            save_path=None,
            show=False,
        )
        self._last_results = {
            "migration": {
                "time_points": time_points,
                "migrated_mass": migrated_mass,
                "figure": migration_fig,
            },
            "migration_by_layer": {
                "time_points": layer_time_points,
                "migrated_mass_by_layer": migrated_mass_by_layer,
                "figure": migration_by_layer_fig,
            },
            "concentration": {
                "C_values": C_values,
                "C_init": C_init,
                "x": x,
                "layers": layers,
                "dt": dt,
                "figure": concentration_fig,
            },
        }
        figures = [
            ("Berechnungsergebnis - Migrationsberechnung", migration_fig, self._export_migration_csv, "migration"),
            ("Konzentrationsprofile", concentration_fig, self._export_concentration_csv, "concentration"),
            ("Migration je Schicht", migration_by_layer_fig, self._export_migration_by_layer_csv, "migration_by_layer"),
        ]
        self._show_results_dialogs(figures)

    def _show_results_dialogs(self, figures):
        valid_figures = [
            (title, fig, export_cb, kind)
            for title, fig, export_cb, kind in figures
            if fig is not None
        ]
        if not valid_figures:
            return

        # Vorherige Ergebnisfenster schließen
        for dlg in getattr(self, "results_dialogs", []):
            try:
                dlg.close()
            except RuntimeError:
                pass
        self.results_dialogs = []

        for title, fig, export_cb, kind in valid_figures:
            dialog = QDialog(self)
            dialog.setWindowTitle(title or "Berechnungsergebnis")
            dialog.setAttribute(Qt.WA_DeleteOnClose, True)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(12)

            canvas = FigureCanvas(fig)
            canvas.draw()
            layout.addWidget(canvas)

            summary = self._build_results_summary(kind)
            if summary:
                summary_label = QLabel(summary)
                summary_label.setWordWrap(True)
                layout.addWidget(summary_label)

            button_row = QHBoxLayout()
            button_row.addStretch(1)

            save_btn = QPushButton("Plot speichern")
            save_btn.setProperty("appStyle", False)
            save_btn.setAutoDefault(False)
            save_btn.clicked.connect(lambda _, f=fig: self._save_plot(f))
            button_row.addWidget(save_btn)

            if export_cb:
                export_btn = QPushButton("CSV exportieren")
                export_btn.setProperty("appStyle", False)
                export_btn.setAutoDefault(False)
                export_btn.clicked.connect(export_cb)
                button_row.addWidget(export_btn)

            layout.addLayout(button_row)

            dialog.resize(1000, 600)
            dialog.show()
            self.results_dialogs.append(dialog)

    def _build_results_summary(self, kind: str) -> str:
        if kind == "migration":
            data = self._last_results.get("migration") or {}
            time_points = data.get("time_points")
            migrated_mass = data.get("migrated_mass")
            if time_points is None or migrated_mass is None or len(time_points) == 0 or len(migrated_mass) == 0:
                return ""
            max_idx = int(np.argmax(migrated_mass))
            max_migration = float(migrated_mass[max_idx])
            max_time_days = float(time_points[max_idx]) / 86400.0
            last_migration = float(migrated_mass[-1])
            last_time_days = float(time_points[-1]) / 86400.0
            dt = self._last_results.get("concentration", {}).get("dt")
            layers = self._last_results.get("concentration", {}).get("layers") or []
            total_d = sum(layer.d for layer in layers) if layers else None
            dt_text = f"{dt:.3g} s" if isinstance(dt, (int, float)) else "-"
            thickness_text = f"{total_d:.3g} cm" if total_d is not None else "-"
            return (
                "<b>Zusammenfassung</b><br>"
                f"Max. Migration: {max_migration:.3g} mg/dm² bei {max_time_days:.3g} Tagen<br>"
                f"Endwert: {last_migration:.3g} mg/dm² nach {last_time_days:.3g} Tagen<br>"
                f"Δt: {dt_text}; Schichten: {len(layers)}; Gesamtstärke: {thickness_text}"
            )

        if kind == "concentration":
            data = self._last_results.get("concentration") or {}
            layers = data.get("layers") or []
            dt = data.get("dt")
            total_d = sum(layer.d for layer in layers) if layers else None
            time_points = self._last_results.get("migration", {}).get("time_points")
            last_time_days = float(time_points[-1]) / 86400.0 if time_points is not None and len(time_points) else None
            dt_text = f"{dt:.3g} s" if isinstance(dt, (int, float)) else "-"
            thickness_text = f"{total_d:.3g} cm" if total_d is not None else "-"
            time_text = f"{last_time_days:.3g} Tage" if last_time_days is not None else "-"
            materials = ", ".join([layer.material for layer in layers]) if layers else "-"
            return (
                "<b>Zusammenfassung</b><br>"
                f"Schichten: {len(layers)}; Materialien: {materials}<br>"
                f"Gesamtstärke: {thickness_text}; Simulationsdauer: {time_text}; Δt: {dt_text}"
            )

        return ""

    def _save_plot(self, figure):
        if figure is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Plot speichern",
            "",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            figure.savefig(path)
        except Exception:
            pass  # Wir unterdrücken Fehlermeldungen; GUI bleibt responsiv

    def _export_migration_csv(self):
        data = self._last_results.get("migration") or {}
        time_points = data.get("time_points")
        migrated_mass = data.get("migrated_mass")
        if time_points is None or migrated_mass is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Ergebnisse exportieren",
            "",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Zeit [Tage]", "Migrierte Masse"])
                for t, mass in zip(time_points, migrated_mass):
                    writer.writerow([t / 86400.0, mass])
        except Exception:
            pass

    def _export_migration_by_layer_csv(self):
        data = self._last_results.get("migration_by_layer") or {}
        time_points = data.get("time_points")
        migrated_by_layer = data.get("migrated_mass_by_layer")
        layers = self._last_results.get("concentration", {}).get("layers") or []
        if time_points is None or migrated_by_layer is None or not layers:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Ergebnisse exportieren",
            "",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="") as handle:
                writer = csv.writer(handle)
                header = ["Zeit [Tage]"]
                for idx, layer in enumerate(layers):
                    header.append(f"Layer {idx + 1} ({layer.material})")
                writer.writerow(header)

                series_list = list(migrated_by_layer)
                min_len = min(len(time_points), *(len(series) for series in series_list))
                for i in range(min_len):
                    row = [time_points[i] / 86400.0]
                    for series in series_list:
                        row.append(series[i])
                    writer.writerow(row)
        except Exception:
            pass

    def _export_concentration_csv(self):
        data = self._last_results.get("concentration") or {}
        C_values = data.get("C_values")
        C_init = data.get("C_init")
        x = data.get("x")
        dt = data.get("dt")
        layers = data.get("layers")
        if C_values is None or C_init is None or x is None or dt is None or not layers:
            return

        time_steps = np.linspace(0, len(C_values) - 1, num=10, dtype=int).astype(int)
        headers = ["x [cm]", "Schicht"]
        for t in time_steps:
            time_days = (t * dt) / 86400.0
            headers.append(f"t={time_days:.3g} d")

        # Zuordnung jeder x-Position zur passenden Schicht
        layer_spans = []
        current = x[0]
        for layer in layers:
            end = current + layer.d
            layer_spans.append((current, end, layer.material))
            current = end

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Ergebnisse exportieren",
            "",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                for idx, pos in enumerate(x):
                    # Bestimme Schichtname für diese Position
                    layer_name = ""
                    for start, end, name in layer_spans:
                        if start <= pos < end or abs(pos - end) < 1e-9:
                            layer_name = name
                            break
                    row = [pos, layer_name]
                    for t in time_steps:
                        if t == 0:
                            row.append(C_init[idx])
                        else:
                            row.append(C_values[t][idx])
                    writer.writerow(row)
        except Exception:
            pass


class MultiLayerSuiteTab(QWidget):
    """
    Container-Tab für das Multi-Layer-Modell mit eigenen Unter-Tabs.
    Aktuell nur 'Migrationsberechnung', kann bei Bedarf erweitert werden.
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(MultiLayerTab(), "Migrationsberechnung")
        layout.addWidget(self.sub_tabs)
