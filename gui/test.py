from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Create main vertical layout
        main_layout = QVBoxLayout()

        # Create a horizontal layout for the top section
        top_layout = QHBoxLayout()
        label = QLabel("Hello, World!")
        button = QPushButton("Click Me")
        top_layout.addWidget(label)
        top_layout.addWidget(button)

        # Add the top layout to the main layout
        main_layout.addLayout(top_layout)

        # Create a vertical layout for the bottom section
        bottom_layout = QVBoxLayout()
        label2 = QLabel("This is a label.")
        button2 = QPushButton("Another Button")
        bottom_layout.addWidget(label2)
        bottom_layout.addWidget(button2)

        # Add the bottom layout to the main layout
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

if __name__ == "__main__":
    app = QApplication([])
    window = MyWidget()
    window.show()
    app.exec_()