import os
from typing import List, Tuple

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
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

        self.label_width = 90
        self.input_width = 120
        self.unit_width = 40

        self._build_ui()
        self._add_default_rows()

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

        table_label = QLabel("<b>Messwerte</b>")
        table_layout.addWidget(table_label)

        self.measurement_table = QTableWidget(0, 2)
        self.measurement_table.setHorizontalHeaderLabels(["Zeit [Tage]", "Messwert [mg/kg]"])
        header = self.measurement_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        table_layout.addWidget(self.measurement_table)

        table_button_layout = QHBoxLayout()
        table_button_layout.setSpacing(6)
        add_row_button = QPushButton("Zeile hinzufügen")
        add_row_button.clicked.connect(self._add_row)
        remove_row_button = QPushButton("Zeile entfernen")
        remove_row_button.clicked.connect(self._remove_selected_row)
        table_button_layout.addWidget(add_row_button)
        table_button_layout.addWidget(remove_row_button)
        table_button_layout.addStretch()
        table_layout.addLayout(table_button_layout)

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

    def _add_row(self) -> None:
        row = self.measurement_table.rowCount()
        self.measurement_table.insertRow(row)
        for col in range(2):
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.measurement_table.setItem(row, col, item)

    def _remove_selected_row(self) -> None:
        selected_rows = {index.row() for index in self.measurement_table.selectionModel().selectedIndexes()}
        if not selected_rows and self.measurement_table.rowCount() > 0:
            self.measurement_table.removeRow(self.measurement_table.rowCount() - 1)
            return
        for row in sorted(selected_rows, reverse=True):
            self.measurement_table.removeRow(row)

    def _browse_plot_dir(self) -> None:
        current_dir = self.plot_dir_input.text() or os.getcwd()
        selected_dir = QFileDialog.getExistingDirectory(self, "Plot-Ordner auswählen", current_dir)
        if selected_dir:
            self.plot_dir_input.setText(selected_dir)

    def calculate_coefficient(self) -> None:
        self._set_error("")
        self.result_label.setText("")

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

    def _require_text(self, widget: QLineEdit, field_name: str) -> str:
        text = widget.text().strip()
        if not text:
            raise ValueError(f"{field_name} darf nicht leer sein.")
        return text

    def _parse_float(self, widget: QLineEdit, field_name: str) -> float:
        text = self._require_text(widget, field_name)
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} muss eine Zahl sein.") from exc

    def _set_error(self, message: str) -> None:
        self.error_label.setText(message)
        if message:
            QMessageBox.warning(self, "Eingabefehler", message)

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
