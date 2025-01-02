from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QCheckBox, QLabel
from PySide6.QtCore import Qt


class CheckboxExample(QWidget):
    def __init__(self):
        super().__init__()

        # Fenster-Titel und Größe festlegen
        self.setWindowTitle("Checkbox und Eingabefeld")
        self.setGeometry(100, 100, 300, 150)

        # Hauptlayout erstellen
        layout = QVBoxLayout(self)

        # Checkbox erstellen
        self.checkbox = QCheckBox("Aktiviere Eingabefeld")
        self.checkbox.setChecked(True)  # Standard: aktiviert

        # Eingabefeld erstellen
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Gib hier etwas ein...")
        self.input_field.setEnabled(True)  # Eingabefeld initial aktiv

        # Label für Debugging-Ausgabe
        self.debug_label = QLabel("Eingabefeld: aktiviert")

        # Signal und Slot verbinden
        self.checkbox.toggled.connect(self.toggle_input_field)

        # Widgets zum Layout hinzufügen
        layout.addWidget(self.checkbox)
        layout.addWidget(self.input_field)
        layout.addWidget(self.debug_label)

    def toggle_input_field(self, checked):
        """Aktiviert oder deaktiviert das Eingabefeld basierend auf der Checkbox."""
        self.input_field.setEnabled(checked)
        self.debug_label.setText("Eingabefeld: aktiviert" if checked else "Eingabefeld: deaktiviert")
        print("Checkbox toggled:", checked)
        print("Is input_field enabled?", self.input_field.isEnabled())


if __name__ == "__main__":
    app = QApplication([])  # QApplication initialisieren
    window = CheckboxExample()  # Instanz der Klasse erstellen
    window.show()  # Fenster anzeigen
    app.exec()  # Event-Loop starten
