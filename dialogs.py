"""Dialog windows for search sources and history."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QCheckBox, QDialogButtonBox, QPushButton, QMessageBox, QAbstractItemView,
    QLineEdit, QLabel
)
from PyQt6.QtCore import Qt
from browser_search import BrowserSearch
from history_manager import HistoryManager
from utils import log_action

import re

class SearchSourcesDialog(QDialog):
    def __init__(self, sources, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Sources")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget)

        self.checkboxes = {}
        for source, enabled in sources.items():
            item = QListWidgetItem()
            self.list_widget.addItem(item)
            cb = QCheckBox(BrowserSearch.get_source_display_name(source))
            cb.setChecked(enabled)
            self.list_widget.setItemWidget(item, cb)
            self.checkboxes[source] = cb

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_sources(self):
        return {src: cb.isChecked() for src, cb in self.checkboxes.items()}


class SearchHistoryDialog(QDialog):
    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search History")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.history_manager = history_manager

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.rerun_btn = QPushButton("Rerun Selected")
        self.rerun_btn.clicked.connect(self.rerun_selected)
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(self.rerun_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for entry in self.history_manager.get_history():
            query = entry['query']
            timestamp = entry.get('display_time', entry['timestamp'])
            sources = ', '.join([BrowserSearch.get_source_display_name(s) for s, e in entry['sources'].items() if e])
            text = f"{timestamp} - {query} [{sources}]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list_widget.addItem(item)

    def on_item_double_clicked(self, item):
        entry = item.data(Qt.ItemDataRole.UserRole)
        self.rerun_search(entry)

    def rerun_selected(self):
        item = self.list_widget.currentItem()
        if item:
            entry = item.data(Qt.ItemDataRole.UserRole)
            self.rerun_search(entry)

    def rerun_search(self, entry):
        query = entry['query']
        sources = entry['sources']
        BrowserSearch.search_all_sources(query, sources)
        log_action(f"Re-ran search from history: '{query}'")

    def clear_history(self):
        reply = QMessageBox.question(self, "Confirm", "Clear all search history?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_history()
            self.refresh_list()
            log_action("Search history cleared")

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setModal(True)
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter password to unlock credentials:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_password(self):
        return self.password_edit.text()

def password_meets_requirements(password):
    """Check password strength. Returns (bool, message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    if not has_upper:
        return False, "Password must contain at least one uppercase letter."
    if not has_lower:
        return False, "Password must contain at least one lowercase letter."
    if not has_digit:
        return False, "Password must contain at least one number."
    if not has_symbol:
        return False, "Password must contain at least one symbol (e.g., !@#$%^&*)."
    return True, ""


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First Time Setup")
        self.setModal(True)
        self.setFixedSize(450, 450)

        layout = QVBoxLayout(self)

        # Instructions
        layout.addWidget(QLabel("Welcome! Please set up your Zoho credentials."))
        layout.addWidget(QLabel("These will be stored encrypted with a master password."))
        layout.addSpacing(10)

        # Username (optional)
        layout.addWidget(QLabel("Username (optional):"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)

        # Zoho credentials
        layout.addWidget(QLabel("Zoho Client ID:"))
        self.client_id_edit = QLineEdit()
        layout.addWidget(self.client_id_edit)

        layout.addWidget(QLabel("Zoho Client Secret:"))
        self.client_secret_edit = QLineEdit()
        self.client_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.client_secret_edit)

        layout.addWidget(QLabel("Zoho Refresh Token:"))
        self.refresh_token_edit = QLineEdit()
        self.refresh_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.refresh_token_edit)

        layout.addWidget(QLabel("Zoho Organization ID:"))
        self.org_id_edit = QLineEdit()
        layout.addWidget(self.org_id_edit)

        # Master password with requirements
        layout.addSpacing(10)
        layout.addWidget(QLabel("Set a master password to encrypt credentials:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setPlaceholderText("Confirm password")
        layout.addWidget(self.confirm_edit)

        # Password requirements label
        self.req_label = QLabel(
            "Password must be at least 8 characters and include:\n"
            "• one uppercase letter\n"
            "• one lowercase letter\n"
            "• one number\n"
            "• one symbol (e.g., !@#$%^&*)"
        )
        self.req_label.setWordWrap(True)
        self.req_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.req_label)

        layout.addSpacing(10)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate(self):
        # Check that passwords match
        if self.password_edit.text() != self.confirm_edit.text():
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        # Check password strength
        ok, msg = password_meets_requirements(self.password_edit.text())
        if not ok:
            QMessageBox.warning(self, "Weak Password", msg)
            return

        # Check required fields
        if not self.client_id_edit.text() or not self.client_secret_edit.text() \
                or not self.refresh_token_edit.text() or not self.org_id_edit.text():
            QMessageBox.warning(self, "Error", "All Zoho fields are required.")
            return

        self.accept()

    def get_data(self):
        return {
            "username": self.username_edit.text().strip() or None,
            "client_id": self.client_id_edit.text().strip(),
            "client_secret": self.client_secret_edit.text().strip(),
            "refresh_token": self.refresh_token_edit.text().strip(),
            "org_id": self.org_id_edit.text().strip(),
        }

    def get_password(self):
        return self.password_edit.text()


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Password")
        self.setModal(True)
        self.setFixedSize(350, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Current Password:"))
        self.current_edit = QLineEdit()
        self.current_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.current_edit)

        layout.addWidget(QLabel("New Password:"))
        self.new_edit = QLineEdit()
        self.new_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_edit)

        layout.addWidget(QLabel("Confirm New Password:"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_edit)

        # Password requirements label
        self.req_label = QLabel(
            "Password must be at least 8 characters and include:\n"
            "• one uppercase letter\n"
            "• one lowercase letter\n"
            "• one number\n"
            "• one symbol (e.g., !@#$%^&*)"
        )
        self.req_label.setWordWrap(True)
        self.req_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.req_label)

        layout.addSpacing(10)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate(self):
        # Check that new passwords match
        if self.new_edit.text() != self.confirm_edit.text():
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            return

        # Check password strength
        ok, msg = password_meets_requirements(self.new_edit.text())
        if not ok:
            QMessageBox.warning(self, "Weak Password", msg)
            return

        if not self.current_edit.text():
            QMessageBox.warning(self, "Error", "Current password required.")
            return

        self.accept()

    def get_current(self):
        return self.current_edit.text()

    def get_new(self):
        return self.new_edit.text()