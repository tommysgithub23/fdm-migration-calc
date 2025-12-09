from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QLineEdit, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QSizePolicy, QComboBox, QApplication, QDialog, QMenu, QTabWidget
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QPalette
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from ml_model_functions import Layer, run_simulation, plot_results, plot_migrated_mass_over_time, calculate_migrated_mass_over_time
from tooltip_helper import DelayedToolTipHelper


class MultiLayerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.material_list = ["LDPE", "LLDPE", "HDPE", "PP", "PET", "PS", "PEN", "HIPS"]
        self.tooltip_helper = DelayedToolTipHelper(parent=self)
        self.label_width = 60
        self.input_width = 90
        self.unit_width = 20

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
        self.T_C_input = QLineEdit("40")
        self.M_r_input = QLineEdit("531")
        self.t_max_input = QLineEdit("1")
        self.d_nx_input = QLineEdit("0.02")
        self.tooltip_helper.register(self.T_C_input, "Temperatur der Simulation in °C.")
        self.tooltip_helper.register(self.M_r_input, "Relative Molekülmasse des Migranten in g/mol.")
        self.tooltip_helper.register(self.t_max_input, "Gesamtdauer der Simulation in Tagen (wird in Sekunden umgerechnet).")
        self.tooltip_helper.register(self.d_nx_input, "Verhältnis von Schichtdicke zu räumlicher Diskretisierung d/nₓ in cm.")

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
        self.layer_table = QTableWidget(0, 5)
        headers = ["Material", "d (cm)", "nₓ", "Kₓ", "C₀ (mg/kg)"]
        self.layer_table.setHorizontalHeaderLabels(headers)
        self.column_tooltips = {
            0: "Materialtyp der Schicht.",
            1: "Schichtdicke d in Zentimetern.",
            2: "Anzahl der Diskretisierungselemente nₓ.",
            3: "Verteilungskoeffizient Kₓ zur nächsten Schicht.",
            4: "Anfangskonzentration C₀ der Schicht in mg/kg."
        }
        for col, text in self.column_tooltips.items():
            header_item = self.layer_table.horizontalHeaderItem(col)
            if header_item:
                header_item.setToolTip(text)
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
        graphics_label = QLabel("<b>Grafische Darstellung der Schichten</b>")
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
            self.d_nx_input,
        )
        for field in scalar_fields:
            if self.is_valid_number(field.text()):
                self.mark_field_valid(field)
            else:
                self.mark_field_invalid(field)
                is_valid = False

        for row in range(self.layer_table.rowCount()):
            for col in (1, 2, 3, 4):
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
        if col in (1, 2, 3, 4):
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
        default_values = ["0.2", "10", "1.0", "0.0"]
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

        default_values = ["2.0", "10", "1.0", "0.0"]
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
        # t_max wird in Tagen eingegeben → in Sekunden umrechnen
        t_max_days = float(self.t_max_input.text())
        t_max = t_max_days * 24 * 3600
        # Verwende festen Zeitschritt (kann später als Eingabe ergänzt werden)
        dt = 1.0  

        # 4) Layer-Liste bauen
        layers = []
        for row in range(self.layer_table.rowCount()):
            material = self.get_material_from_row(row)
            d       = float(self.layer_table.item(row, 1).text())
            nx      = int(float(self.layer_table.item(row, 2).text()))
            K_val   = float(self.layer_table.item(row, 3).text())
            C_init  = float(self.layer_table.item(row, 4).text())
            layer = Layer(material, d, nx, K_val, C_init)       # :contentReference[oaicite:3]{index=3}
            layer.set_diffusion_coefficient(M_r, T_C)            # :contentReference[oaicite:4]{index=4}
            layers.append(layer)

        C_values, C_init, total_masses, x, partitioning = run_simulation(layers, t_max, dt)  # :contentReference[oaicite:5]{index=5}&#8203;:contentReference[oaicite:6]{index=6}

        concentration_fig = plot_results(C_values, C_init, x, layers, dt, show=False)

        migrated_mass, time_points = calculate_migrated_mass_over_time(
            C_values, x, layers, dt, calc_interval=1
        )

        migration_fig = plot_migrated_mass_over_time(migrated_mass, time_points, save_path=None, show=False)
        self._show_results_dialog([migration_fig, concentration_fig])

    def _show_results_dialog(self, figures):
        valid_figures = [fig for fig in figures if fig is not None]
        if not valid_figures:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Berechnungsergebnisse")
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        for fig in valid_figures:
            canvas = FigureCanvas(fig)
            canvas.draw()
            layout.addWidget(canvas)

        close_button = QPushButton("Schließen")
        close_button.setProperty("appStyle", True)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        dialog.resize(800, 1200)
        dialog.show()
        self.results_dialog = dialog


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
