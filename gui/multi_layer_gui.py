from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QFormLayout, QLineEdit, QHBoxLayout, QGraphicsView, QGraphicsScene, QSizePolicy, QSpacerItem, QComboBox, QTableWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon


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

        # --- Eingabebereich (links) ---
        self.input_layout = QVBoxLayout()
        self.T_C_input = QLineEdit("40")
        self.M_r_input = QLineEdit("531")
        self.t_max_input = QLineEdit("10")

        # Nutze addWidget und setze die Elemente linksbündig
        self.input_layout.addWidget(self._create_labeled_row("T<sub>C</sub>", "°C", self.T_C_input))
        self.input_layout.addWidget(self._create_labeled_row("M<sub>r</sub>", "g/mol", self.M_r_input))
        self.input_layout.addWidget(self._create_labeled_row("t<sub>max</sub>", "Tage", self.t_max_input))
        self.input_layout.setAlignment(Qt.AlignLeft)  # Links-Ausrichtung für den gesamten Eingabebereich

        # --- Schichtentabelle (rechts) ---
        self.layer_table = QTableWidget(0, 5)
        self.layer_table.setHorizontalHeaderLabels(["Material", "d (cm)", "nₓ", "Kₓ", "C₀ (mg/kg)"])
        self.layer_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)

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

        # Start-Button
        self.start_button = QPushButton("Simulation starten")
        self.main_layout.addWidget(self.start_button)
        self.main_layout.setAlignment(self.start_button, Qt.AlignCenter)

        # Fehler-Label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.main_layout.addWidget(self.error_label)

        # Tabelle mit zwei Spalten als Start vorbereiten
        self.add_layer()
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

    def add_layer(self):
        """Fügt eine neue Schicht hinzu."""
        row_count = self.layer_table.rowCount()
        self.layer_table.insertRow(row_count)

        # --- Spalte 0: Material-Dropdown ---
        material_dropdown = QComboBox()
        material_dropdown.addItems(self.material_list)
        self.layer_table.setCellWidget(row_count, 0, material_dropdown)

        # --- Spalten 1 bis 4: normale Eingabefelder ---
        default_values = ["0.0", "10", "1.0", "0.0"]
        for col, value in enumerate(default_values, start=1):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            self.layer_table.setItem(row_count, col, item)
    
    def get_material_from_row(self, row):
        widget = self.layer_table.cellWidget(row, 0)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return None

    def remove_layer(self):
        """Entfernt die letzte Schicht."""
        row_count = self.layer_table.rowCount()
        if row_count > 0:
            self.layer_table.removeRow(row_count - 1)
