import os
from typing import List, Tuple

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QSizePolicy,
    QMenu,
)

from sl_model_curve_fitting import (
    find_optimized_D_P,
    migrationsmodell_piringer_for_curve_fitting,
    plot_migration_results,
)


class CurveFittingTab(QWidget):
    """
    Tab zur Ermittlung des Diffusionskoeffizienten anhand von Messwerten.
    """

    def __init__(self):
        super().__init__()

        self.canvas: FigureCanvas | None = None
        self.saved_plot_path: str | None = None
        self._validation_message: str = ""

        self.label_width = 90
        self.input_width = 120
        self.unit_width = 40

        self._build_ui()
        self._add_default_rows()
        self._register_validation_hooks()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "measurement_table", None) and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.measurement_table.rowCount() > 0 and self.measurement_table.currentRow() == self.measurement_table.rowCount() - 1:
                    self._add_row(start_edit=True, copy_column=self.measurement_table.currentColumn())
                    return True
        return super().eventFilter(obj, event)

    def _build_ui(self) -> None:
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

        self.surrogate_input = QLineEdit()
        self.temperature_input = QLineEdit("20")
        self.c_p0_input = QLineEdit("820")
        self.p_density_input = QLineEdit("0.9045")
        self.f_density_input = QLineEdit("0.9")
        self.k_pf_input = QLineEdit("1")
        self.v_p_input = QLineEdit("10.6384")
        self.v_f_input = QLineEdit("28.27")
        self.a_pf_input = QLineEdit("0.2827")
        self.dt_input = QLineEdit("3600")
        default_plot_dir = os.path.join(os.getcwd(), "data", "plots")
        self.plot_dir_input = QLineEdit(default_plot_dir)
        self.plot_dir_input.setMinimumWidth(220)

        self._configure_line_edit(self.surrogate_input, align_left=True)
        for fld in (
            self.temperature_input,
            self.c_p0_input,
            self.p_density_input,
            self.f_density_input,
            self.k_pf_input,
            self.v_p_input,
            self.v_f_input,
            self.a_pf_input,
            self.dt_input,
        ):
            self._configure_line_edit(fld)

        left_column = QVBoxLayout()
        left_column.setSpacing(6)
        left_column.setContentsMargins(0, 0, 0, 0)

        inputs_headline = QLabel("<b>Eingabeparameter</b>")
        inputs_headline.setAlignment(Qt.AlignLeft)
        left_column.addWidget(inputs_headline)

        self.input_layout = QVBoxLayout()
        self.input_layout.setSpacing(6)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        left_column.addLayout(self.input_layout)

        self.input_layout.addWidget(self._create_labeled_row("Surrogat", "", self.surrogate_input))
        self.input_layout.addWidget(self._create_labeled_row("T<sub>C</sub>", "°C", self.temperature_input))
        self.input_layout.addWidget(self._create_labeled_row("c<sub>P0</sub>", "mg/kg", self.c_p0_input))
        self.input_layout.addWidget(self._create_labeled_row("ρ<sub>P</sub>", "g/cm³", self.p_density_input))
        self.input_layout.addWidget(self._create_labeled_row("ρ<sub>F</sub>", "g/cm³", self.f_density_input))
        self.input_layout.addWidget(self._create_labeled_row("K<sub>PF</sub>", "-", self.k_pf_input))
        self.input_layout.addWidget(self._create_labeled_row("V<sub>P</sub>", "cm³", self.v_p_input))
        self.input_layout.addWidget(self._create_labeled_row("V<sub>F</sub>", "cm³", self.v_f_input))
        self.input_layout.addWidget(self._create_labeled_row("A<sub>PF</sub>", "dm²", self.a_pf_input))
        self.input_layout.addWidget(self._create_labeled_row("Δt", "s", self.dt_input))

        plot_dir_widget = QWidget()
        plot_dir_layout = QHBoxLayout(plot_dir_widget)
        plot_dir_layout.setSpacing(6)
        plot_dir_layout.setContentsMargins(0, 0, 0, 0)
        plot_dir_layout.addWidget(self.plot_dir_input, 1)
        browse_button = QPushButton("Ordner wählen")
        browse_button.clicked.connect(self._browse_plot_dir)
        plot_dir_layout.addWidget(browse_button)
        self.input_layout.addWidget(self._create_labeled_row("Plot Pfad", "", plot_dir_widget))

        left_column.addStretch()
        top_layout.addLayout(left_column, 0)

        table_layout = QVBoxLayout()
        table_layout.setSpacing(6)
        table_layout.setContentsMargins(0, 0, 0, 0)

        table_label = QLabel("<b>Messwerte</b>")
        table_header_layout = QHBoxLayout()
        table_header_layout.setSpacing(6)
        table_header_layout.addWidget(table_label)
        table_header_layout.addStretch()
        import_button = QPushButton("Excel importieren")
        import_button.setFixedHeight(26)
        import_button.clicked.connect(self._import_measurements_from_excel)
        table_header_layout.addWidget(import_button)
        table_layout.addLayout(table_header_layout)

        self.measurement_table = QTableWidget(0, 2)
        self.measurement_table.setHorizontalHeaderLabels(["Zeit [Tage]", "Messwert [mg/kg]"])
        header = self.measurement_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        table_layout.addWidget(self.measurement_table)
        self.measurement_table.installEventFilter(self)
        self.measurement_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.measurement_table.customContextMenuRequested.connect(self._show_measurement_context_menu)

        top_layout.addLayout(table_layout, 1)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        self.calculate_button = QPushButton("Diffusionskoeffizient berechnen")
        self.calculate_button.clicked.connect(self.calculate_coefficient)
        controls_layout.addStretch()
        controls_layout.addWidget(self.calculate_button)
        self.main_layout.addLayout(controls_layout)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignLeft)
        self.result_label.setWordWrap(True)
        self.main_layout.addWidget(self.result_label)

    def _add_default_rows(self) -> None:
        for _ in range(3):
            self._add_row()

    def _add_row(self, start_edit: bool = False, copy_column: int | None = None) -> None:
        row = self.measurement_table.rowCount()
        self.measurement_table.insertRow(row)
        for col in range(2):
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.measurement_table.setItem(row, col, item)

        if start_edit:
            target_col = copy_column if copy_column in (0, 1) else 0
            self.measurement_table.setCurrentCell(row, target_col)
            self.measurement_table.editItem(self.measurement_table.item(row, target_col))

    def _remove_selected_row(self, row: int | None = None) -> None:
        if row is not None:
            selected_rows = {row}
        else:
            selected_rows = {index.row() for index in self.measurement_table.selectionModel().selectedIndexes()}
        if not selected_rows and self.measurement_table.rowCount() > 0:
            selected_rows = {self.measurement_table.rowCount() - 1}
        for row_idx in sorted(selected_rows, reverse=True):
            self.measurement_table.removeRow(row_idx)

    def _show_measurement_context_menu(self, pos) -> None:
        index = self.measurement_table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        remove_action = menu.addAction("Zelle entfernen")
        action = menu.exec(self.measurement_table.mapToGlobal(pos))
        if action == remove_action:
            self._remove_selected_row(index.row())

    def _import_measurements_from_excel(self) -> None:
        self._set_error("", show_dialog=False)
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
                raise ValueError("Datei benötigt mindestens zwei Spalten (Zeit, Messwert).")

            df = df.iloc[:, :2].dropna()
            if df.empty:
                raise ValueError("Keine Daten gefunden.")

            self.measurement_table.setRowCount(0)
            for _, (time_val, meas_val) in df.iterrows():
                row = self.measurement_table.rowCount()
                self.measurement_table.insertRow(row)
                for col, val in enumerate((time_val, meas_val)):
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.measurement_table.setItem(row, col, item)
            # Nach Import ersten Eintrag fokussieren
            if self.measurement_table.rowCount() > 0:
                self.measurement_table.setCurrentCell(0, 0)
        except Exception as exc:
            self._set_error(f"Import fehlgeschlagen: {exc}")

    def _browse_plot_dir(self) -> None:
        current_dir = self.plot_dir_input.text() or os.getcwd()
        selected_dir = QFileDialog.getExistingDirectory(self, "Plot-Ordner auswählen", current_dir)
        if selected_dir:
            self.plot_dir_input.setText(selected_dir)

    def calculate_coefficient(self) -> None:
        self._set_error("", show_dialog=False)
        self.result_label.setText("")

        if not self.validate_inputs():
            message = self._validation_message or "Bitte korrigiere die rot markierten Felder."
            self._set_error(message, show_dialog=False)
            return

        try:
            surrogate = self._require_text(self.surrogate_input, "Surrogat")
            temperature = self._parse_float(self.temperature_input, "Temperatur")
            c_p0 = self._parse_float(self.c_p0_input, "cₚ₀")
            p_density = self._parse_float(self.p_density_input, "ρₚ")
            f_density = self._parse_float(self.f_density_input, "ρ_F")
            k_pf = self._parse_float(self.k_pf_input, "K_PF")
            v_p = self._parse_float(self.v_p_input, "V_P")
            v_f = self._parse_float(self.v_f_input, "V_F")
            a_pf = self._parse_float(self.a_pf_input, "A_PF")
            dt = self._parse_float(self.dt_input, "Δt")
            plot_dir = self.plot_dir_input.text().strip()
            if not plot_dir:
                raise ValueError("Bitte einen Plot-Ordner angeben.")

            measurement_days, c_f_values = self._collect_measurements()
        except ValueError as exc:
            self._set_error(str(exc))
            return

        measurement_seconds = np.array(measurement_days) * 24 * 3600
        t_max = float(np.max(measurement_seconds))
        d_P = v_p / (a_pf * 1e2)
        d_F = v_f / (a_pf * 1e2)
        m_F = v_f * f_density * 1e-3
        measured_values = (np.array(c_f_values) / a_pf) * m_F

        measurement_point = {
            "surrogate": surrogate,
            "temperature_C": temperature,
            "c_P0": c_p0,
        }

        try:
            D_P_candidates = np.logspace(-12, -6, num=100)
            optimal_D_P = find_optimized_D_P(
                D_P_candidates,
                c_p0,
                p_density,
                k_pf,
                t_max,
                v_p,
                v_f,
                d_P,
                d_F,
                a_pf,
                dt,
                measured_values,
                measurement_seconds,
            )

            optimal_simulation = migrationsmodell_piringer_for_curve_fitting(
                c_p0,
                p_density,
                k_pf,
                t_max,
                v_p,
                v_f,
                d_P,
                d_F,
                a_pf,
                dt,
                optimal_D_P,
            )

            save_path = plot_migration_results(
                t_max,
                dt,
                optimal_simulation,
                measurement_seconds,
                measured_values,
                optimal_D_P,
                measurement_point,
                p_density,
                f_density,
                k_pf,
                c_p0,
                plot_dir,
            )
            figure = self._current_figure()
            self._display_figure(figure)
        except Exception as exc:  # pylint: disable=broad-except
            self._set_error(f"Fehler bei der Berechnung: {exc}")
            return

        self.saved_plot_path = save_path
        self.result_label.setText(
            f"Berechneter Diffusionskoeffizient: {optimal_D_P:.3e} cm²/s\nPlot gespeichert unter: {save_path}"
        )

    def _collect_measurements(self) -> Tuple[List[float], List[float]]:
        times: List[float] = []
        values: List[float] = []
        rows = self.measurement_table.rowCount()

        for row in range(rows):
            time_item = self.measurement_table.item(row, 0)
            value_item = self.measurement_table.item(row, 1)

            time_text = time_item.text().strip() if time_item else ""
            value_text = value_item.text().strip() if value_item else ""

            if not time_text and not value_text:
                continue

            if not time_text or not value_text:
                raise ValueError(f"Bitte Zeile {row + 1} vollständig ausfüllen.")

            try:
                time_value = float(time_text)
                measurement_value = float(value_text)
            except ValueError as exc:
                raise ValueError(f"Ungültiger Messwert in Zeile {row + 1}.") from exc

            if time_value < 0:
                raise ValueError(f"Zeit in Zeile {row + 1} muss ≥ 0 sein.")

            times.append(time_value)
            values.append(measurement_value)

        if len(times) < 2:
            raise ValueError("Bitte mindestens zwei Messpunkte eingeben.")

        return times, values

    def _display_figure(self, figure) -> None:
        if figure is None:
            return
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Migration Plot")
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        layout = QVBoxLayout(dialog)

        canvas = FigureCanvas(figure)
        canvas.draw()
        layout.addWidget(canvas)

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        dialog.resize(1200, 600)
        dialog.show()

    def _current_figure(self):
        import matplotlib.pyplot as plt

        figure = plt.gcf()
        plt.close(figure)
        return figure

    def _register_validation_hooks(self) -> None:
        self.required_text_fields = {
            "Surrogat": self.surrogate_input,
            "Plot Pfad": self.plot_dir_input,
        }
        self.numeric_fields = {
            "Temperatur": self.temperature_input,
            "cₚ₀": self.c_p0_input,
            "ρₚ": self.p_density_input,
            "ρ_F": self.f_density_input,
            "K_PF": self.k_pf_input,
            "V_P": self.v_p_input,
            "V_F": self.v_f_input,
            "A_PF": self.a_pf_input,
            "Δt": self.dt_input,
        }

        for widget in self.required_text_fields.values():
            widget.textChanged.connect(lambda _, w=widget: self._validate_line_edit(w, numeric=False))
        for widget in self.numeric_fields.values():
            widget.textChanged.connect(lambda _, w=widget: self._validate_line_edit(w, numeric=True))

        self.measurement_table.itemChanged.connect(self._on_measurement_item_changed)

    def _on_measurement_item_changed(self, _item: QTableWidgetItem) -> None:
        self._validate_measurement_table()

    def validate_inputs(self) -> bool:
        """Überprüft alle Eingabefelder und Messwerte."""
        self._validation_message = ""
        is_valid = True

        for widget in self.required_text_fields.values():
            if widget.text().strip():
                self.mark_field_valid(widget)
            else:
                self.mark_field_invalid(widget)
                is_valid = False

        for widget in self.numeric_fields.values():
            if self._is_valid_number(widget.text()):
                self.mark_field_valid(widget)
            else:
                self.mark_field_invalid(widget)
                is_valid = False

        measurements_valid, measurement_message = self._validate_measurement_table()
        if not measurements_valid:
            is_valid = False
            if measurement_message:
                self._validation_message = measurement_message

        if not is_valid and not self._validation_message:
            self._validation_message = "Bitte korrigiere die rot markierten Felder."

        if is_valid:
            self.error_label.setText("")

        return is_valid

    def _validate_measurement_table(self) -> Tuple[bool, str | None]:
        is_valid = True
        message: str | None = None
        filled_rows = 0
        for row in range(self.measurement_table.rowCount()):
            time_item = self.measurement_table.item(row, 0)
            value_item = self.measurement_table.item(row, 1)

            time_text = time_item.text().strip() if time_item and time_item.text() else ""
            value_text = value_item.text().strip() if value_item and value_item.text() else ""

            row_has_values = bool(time_text or value_text)
            if not row_has_values:
                self._mark_measurement_cell_valid(row, 0)
                self._mark_measurement_cell_valid(row, 1)
                continue

            # Feldvollständigkeit prüfen
            row_valid = True
            if not time_text:
                self._mark_measurement_cell_invalid(row, 0)
                row_valid = False
                if message is None:
                    message = f"Bitte Zeile {row + 1} vollständig ausfüllen."
            if not value_text:
                self._mark_measurement_cell_invalid(row, 1)
                row_valid = False
                if message is None:
                    message = f"Bitte Zeile {row + 1} vollständig ausfüllen."
            if not row_valid:
                is_valid = False
                continue

            # Zahlen prüfen
            if "," in time_text or "," in value_text:
                self._mark_measurement_cell_invalid(row, 0)
                self._mark_measurement_cell_invalid(row, 1)
                is_valid = False
                if message is None:
                    message = "Bitte '.' als Dezimaltrennzeichen verwenden."
                continue

            try:
                time_value = float(time_text)
                if time_value < 0:
                    raise ValueError
                self._mark_measurement_cell_valid(row, 0)
            except ValueError:
                self._mark_measurement_cell_invalid(row, 0)
                is_valid = False
                if message is None:
                    message = f"Ungültige Zeit in Zeile {row + 1}."

            try:
                float(value_text)
                self._mark_measurement_cell_valid(row, 1)
            except ValueError:
                self._mark_measurement_cell_invalid(row, 1)
                is_valid = False
                if message is None:
                    message = f"Ungültiger Messwert in Zeile {row + 1}."
                continue

            filled_rows += 1

        if filled_rows < 2:
            is_valid = False
            if message is None:
                message = "Bitte mindestens zwei Messpunkte eingeben."

        return is_valid, message

    def _require_text(self, widget: QLineEdit, field_name: str) -> str:
        text = widget.text().strip()
        if not text:
            raise ValueError(f"{field_name} darf nicht leer sein.")
        return text

    def _parse_float(self, widget: QLineEdit, field_name: str) -> float:
        text = self._require_text(widget, field_name)
        try:
            if "," in text:
                raise ValueError(f"{field_name} muss '.' als Dezimaltrennzeichen verwenden.")
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} muss eine Zahl sein.") from exc

    def _set_error(self, message: str, show_dialog: bool = True) -> None:
        self.error_label.setText(message)
        if message and show_dialog:
            QMessageBox.warning(self, "Eingabefehler", message)

    def mark_field_invalid(self, widget: QLineEdit) -> None:
        widget.setStyleSheet("border: 1px solid red;")

    def mark_field_valid(self, widget: QLineEdit) -> None:
        widget.setStyleSheet("")

    def _mark_measurement_cell_invalid(self, row: int, col: int) -> None:
        item = self.measurement_table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.measurement_table.setItem(row, col, item)
        item.setBackground(QColor("#FFCCCC"))

    def _mark_measurement_cell_valid(self, row: int, col: int) -> None:
        item = self.measurement_table.item(row, col)
        if item:
            base_color = self.measurement_table.palette().color(QPalette.Base)
            item.setBackground(base_color)

    def _validate_line_edit(self, widget: QLineEdit, numeric: bool) -> None:
        text = widget.text()
        if numeric:
            is_valid = self._is_valid_number(text)
        else:
            is_valid = bool(text.strip())
        if is_valid:
            self.mark_field_valid(widget)
        else:
            self.mark_field_invalid(widget)

    def _is_valid_number(self, value: str) -> bool:
        txt = value.strip()
        if not txt:
            return False
        if "," in txt:
            if not self._validation_message:
                self._validation_message = "Bitte '.' als Dezimaltrennzeichen verwenden."
            return False
        try:
            float(txt)
            return True
        except ValueError:
            return False

    def _configure_line_edit(self, widget: QLineEdit, align_left: bool = False) -> None:
        widget.setFixedWidth(self.input_width)
        widget.setFixedHeight(25)
        alignment = Qt.AlignLeft if align_left else Qt.AlignRight
        widget.setAlignment(alignment | Qt.AlignVCenter)

    def _create_labeled_row(self, label_text: str, unit_text: str, field_widget) -> QWidget:
        row_layout = QHBoxLayout()
        row_layout.setSpacing(6)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"<html>{label_text}</html>")
        label.setMinimumWidth(self.label_width)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        unit_label = QLabel(unit_text)
        unit_label.setMinimumWidth(self.unit_width)
        unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unit_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        row_layout.addWidget(label)
        row_layout.addWidget(field_widget)
        row_layout.addWidget(unit_label)
        row_layout.addStretch()

        container = QWidget()
        container.setLayout(row_layout)
        return container
