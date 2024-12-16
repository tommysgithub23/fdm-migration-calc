from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MLTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Multi-Layer Model GUI"))
        # Weitere Widgets hinzufügen
        self.setLayout(layout)
