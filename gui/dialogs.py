from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

class CredentialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Telegram API Credentials")
        self.resize(450, 200)

        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QLabel { color: #ffffff; font-size: 14px; font-weight: bold; }
            QLineEdit { background-color: #2d2d2d; border: 1px solid #3d3d3d; border-radius: 4px; padding: 8px; color: #ffffff; font-size: 14px; }
            QPushButton { background-color: #007aff; color: white; border-radius: 4px; padding: 8px 15px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #2089ff; }
        """)

        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.api_id_input = QLineEdit()
        self.api_id_input.setPlaceholderText("e.g., 1234567")
        self.api_id_input.setMinimumHeight(35)

        self.api_hash_input = QLineEdit()
        self.api_hash_input.setPlaceholderText("e.g., a1b2c3d4e5f6g7h8i9j0")
        self.api_hash_input.setMinimumHeight(35)

        layout.addRow("API ID:", self.api_id_input)
        layout.addRow("API Hash:", self.api_hash_input)

        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save && Continue")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #555555;")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)

        layout.addRow(buttons_layout)
        self.setLayout(layout)

    def get_credentials(self):
        return self.api_id_input.text().strip(), self.api_hash_input.text().strip()
