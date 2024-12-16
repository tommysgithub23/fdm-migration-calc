from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class SLTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Single-Layer Model GUI"))
        # Weitere Widgets hinzufügen
        self.setLayout(layout)
