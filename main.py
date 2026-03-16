import sys
import os
import subprocess
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QLineEdit, QPushButton,
    QLabel, QTextEdit, QMessageBox, QCheckBox, QDialog, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor, QAction, QActionGroup

from zoho_api import ZohoClient
from browser_search import BrowserSearch
from history_manager import HistoryManager
from config_manager import ConfigManager
from threads import (
    SyncThread, DetailsThread, StatusUpdateThread,
    DescriptionUpdateThread,
    BrandUpdateThread, FetchBrandsThread
)
from dialogs import SearchSourcesDialog, SearchHistoryDialog, LoginDialog, SetupDialog, ChangePasswordDialog
from utils import (
    log_action, LOG_FILE, COOL_BG, COOL_CARD, COOL_TEXT, WARM_BG, WARM_CARD, WARM_TEXT,
    DARK_BG, DARK_CARD, DARK_TEXT, ACCENT_MINT, ACCENT_PEACH, ACCENT_SALMON,
    ACCENT_LAVENDER, DARK_ACCENT_ACTIVE, DARK_ACCENT_INACTIVE, DARK_ACCENT_SELECT
)
from secure_config import config_exists, load_config, save_config


class InventoryApp(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.config = ConfigManager.load()
        self.current_theme = self.config.get("theme", "dark")
        self._saved_link_state = False
        self._syncing_descriptions = False
        self.selected_item_id = None
        self.loading_details = False
        self.sync_in_progress = False
        self.description_modified = False
        self.link_descriptions = False
        self.brands_list = []  # list of all existing brands

        # Cooldown for Enter key saves
        self.save_cooldown_active = False
        self.save_cooldown_timer = QTimer()
        self.save_cooldown_timer.setSingleShot(True)
        self.save_cooldown_timer.timeout.connect(lambda: setattr(self, 'save_cooldown_active', False))

        self.history_manager = HistoryManager()

        self.setWindowTitle("Inventory Manager")
        self.setGeometry(100, 100, 1400, 700)

        self.create_menu()
        self.setup_ui()
        self.apply_theme(self.current_theme)

        self.load_from_cache()
        self.start_background_sync()

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.auto_sync)
        self.sync_timer.start(300000)

        log_action("Application started")

    def change_password(self):
        dialog = ChangePasswordDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        current = dialog.get_current()
        new = dialog.get_new()
        try:
            data = load_config(current)
        except Exception:
            QMessageBox.warning(self, "Error", "Current password is incorrect.")
            return
        save_config(data, new)
        QMessageBox.information(self, "Success", "Password changed successfully.")

    def create_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        refresh_action = QAction("🔄 Refresh All", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        sources_action = QAction("Search Sources...", self)
        sources_action.triggered.connect(self.open_search_sources)
        settings_menu.addAction(sources_action)

        # Change password under Settings
        change_password_action = QAction("Change Password...", self)
        change_password_action.triggered.connect(self.change_password)
        settings_menu.addAction(change_password_action)

        # View menu
        view_menu = menubar.addMenu("View")
        theme_menu = view_menu.addMenu("🎨 Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        self.theme_cool = QAction("Cool Pastel", self, checkable=True)
        self.theme_cool.triggered.connect(lambda: self.apply_theme("cool"))
        theme_group.addAction(self.theme_cool)
        theme_menu.addAction(self.theme_cool)

        self.theme_warm = QAction("Warm Pastel", self, checkable=True)
        self.theme_warm.triggered.connect(lambda: self.apply_theme("warm"))
        theme_group.addAction(self.theme_warm)
        theme_menu.addAction(self.theme_warm)

        self.theme_dark = QAction("Dark", self, checkable=True)
        self.theme_dark.setChecked(self.current_theme == "dark")
        self.theme_dark.triggered.connect(lambda: self.apply_theme("dark"))
        theme_group.addAction(self.theme_dark)
        theme_menu.addAction(self.theme_dark)

        view_menu.addSeparator()
        show_log_action = QAction("📋 View Activity Log", self)
        show_log_action.triggered.connect(self.open_log_file)
        view_menu.addAction(show_log_action)

        search_history_action = QAction("🔍 Search History", self)
        search_history_action.triggered.connect(self.open_search_history)
        view_menu.addAction(search_history_action)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def open_search_sources(self):
        dialog = SearchSourcesDialog(self.config["search_sources"], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config["search_sources"] = dialog.get_sources()
            ConfigManager.save(self.config)
            log_action("Search sources updated")

    def open_search_history(self):
        dialog = SearchHistoryDialog(self.history_manager, self)
        dialog.exec()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (item list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by name or SKU...")
        self.search_input.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_input)

        self.lock_checkbox = QCheckBox("🔒 Description Locked")
        self.lock_checkbox.setChecked(True)
        self.lock_checkbox.toggled.connect(self.toggle_description_lock)
        search_layout.addWidget(self.lock_checkbox)

        self.link_checkbox = QCheckBox("🔗 Link Descriptions")
        self.link_checkbox.setChecked(False)
        self.link_checkbox.toggled.connect(self.toggle_link_descriptions)
        search_layout.addWidget(self.link_checkbox)

        left_layout.addLayout(search_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "SKU", "Brand", "Stock", "Status"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 120)
        self.tree.setColumnWidth(3, 80)
        self.tree.setColumnWidth(4, 100)
        self.tree.itemSelectionChanged.connect(self.on_item_selected)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_panel)

        # Right panel (details)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.stock_label = QLabel("Stock Info")
        self.stock_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(self.stock_label)

        # Brand row (combo box and update button)
        brand_layout = QHBoxLayout()
        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.setEnabled(False)
        self.brand_combo.setMinimumWidth(200)
        self.brand_combo.setFont(QFont("Arial", 10))
        brand_layout.addWidget(QLabel("Brand:"))
        brand_layout.addWidget(self.brand_combo)
        self.update_brand_btn = QPushButton("Update Brand")
        self.update_brand_btn.setEnabled(False)
        self.update_brand_btn.clicked.connect(self.update_brand)
        brand_layout.addWidget(self.update_brand_btn)
        brand_layout.addStretch()
        right_layout.addLayout(brand_layout)

        self.qty_label = QLabel("")
        self.qty_label.setFont(QFont("Arial", 10))
        right_layout.addWidget(self.qty_label)

        right_layout.addWidget(QLabel("Sales Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setEnabled(False)
        self.desc_edit.textChanged.connect(self.on_description_text_changed)
        self.desc_edit.installEventFilter(self)
        right_layout.addWidget(self.desc_edit)

        right_layout.addWidget(QLabel("Purchase Description:"))
        self.purchase_desc_edit = QTextEdit()
        self.purchase_desc_edit.setMaximumHeight(80)
        self.purchase_desc_edit.setEnabled(False)
        self.purchase_desc_edit.textChanged.connect(self.on_purchase_description_text_changed)
        self.purchase_desc_edit.installEventFilter(self)
        right_layout.addWidget(self.purchase_desc_edit)

        self.save_desc_btn = QPushButton("💾 Save Descriptions")
        self.save_desc_btn.setEnabled(False)
        self.save_desc_btn.clicked.connect(self.save_descriptions)
        right_layout.addWidget(self.save_desc_btn)

        self.toggle_btn = QPushButton("")
        self.toggle_btn.setVisible(False)
        self.toggle_btn.clicked.connect(self.toggle_item_status)
        self.toggle_btn.setFixedHeight(30)
        right_layout.addWidget(self.toggle_btn)

        self.refresh_item_btn = QPushButton("🔄 Refresh Item")
        self.refresh_item_btn.setVisible(False)
        self.refresh_item_btn.clicked.connect(self.refresh_current_item)
        self.refresh_item_btn.setFixedHeight(25)
        right_layout.addWidget(self.refresh_item_btn)

        # Horizontal layout for the two search buttons
        search_buttons_layout = QHBoxLayout()

        self.launch_search_btn = QPushButton("Launch Search")
        self.launch_search_btn.setVisible(False)
        self.launch_search_btn.clicked.connect(self.launch_search)
        self.launch_search_btn.setFixedHeight(25)
        search_buttons_layout.addWidget(self.launch_search_btn)

        self.zoho_search_btn = QPushButton("Zoho Books")
        self.zoho_search_btn.setVisible(False)
        self.zoho_search_btn.clicked.connect(self.launch_zoho_books_search)
        self.zoho_search_btn.setFixedHeight(25)
        search_buttons_layout.addWidget(self.zoho_search_btn)

        right_layout.addLayout(search_buttons_layout)

        right_layout.addSpacing(10)

        self.doc_text = QTextEdit()
        self.doc_text.setReadOnly(True)
        self.doc_text.setFont(QFont("Courier New", 10))
        right_layout.addWidget(self.doc_text)

        splitter.addWidget(right_panel)
        splitter.setSizes([600, 700])

    # ---------- Event filter for Enter key in description fields ----------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                if obj in (self.desc_edit, self.purchase_desc_edit) and not self.lock_checkbox.isChecked() and not self.save_cooldown_active:
                    self.save_descriptions()
                    return True
        return super().eventFilter(obj, event)

    # ---------- Theme ----------
    def apply_theme(self, theme):
        self.current_theme = theme
        self.config["theme"] = theme
        ConfigManager.save(self.config)
        log_action(f"Theme changed to: {theme}")

        if theme == "cool":
            bg = COOL_BG
            card = COOL_CARD
            text = COOL_TEXT
            accent_selected = ACCENT_MINT
            active_color = ACCENT_MINT
            inactive_color = ACCENT_LAVENDER
        elif theme == "warm":
            bg = WARM_BG
            card = WARM_CARD
            text = WARM_TEXT
            accent_selected = ACCENT_PEACH
            active_color = ACCENT_PEACH
            inactive_color = ACCENT_SALMON
        else:  # dark
            bg = DARK_BG
            card = DARK_CARD
            text = DARK_TEXT
            accent_selected = DARK_ACCENT_SELECT
            active_color = DARK_ACCENT_ACTIVE
            inactive_color = DARK_ACCENT_INACTIVE

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(bg))
        palette.setColor(QPalette.ColorRole.Base, QColor(card))
        palette.setColor(QPalette.ColorRole.Text, QColor(text))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
        palette.setColor(QPalette.ColorRole.Button, QColor(card))
        self.setPalette(palette)

        self.tree.setStyleSheet(f"""
            QTreeView {{ background-color: {card}; color: {text}; }}
            QTreeView::item:selected {{ background-color: {accent_selected}; color: white; }}
        """)
        self.doc_text.setStyleSheet(f"background-color: {card}; color: {text};")
        self.desc_edit.setStyleSheet(f"background-color: {card}; color: {text};")
        self.purchase_desc_edit.setStyleSheet(f"background-color: {card}; color: {text};")
        self.search_input.setStyleSheet(f"background-color: {card}; color: {text};")

        self.active_color = active_color
        self.inactive_color = inactive_color
        self.refresh_tree_colors()

    def refresh_tree_colors(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            status = item.text(4)
            if status == 'active':
                item.setBackground(4, QColor(self.active_color))
            else:
                item.setBackground(4, QColor(self.inactive_color))

    # ---------- Link Descriptions ----------
    def toggle_link_descriptions(self, checked):
        self.link_descriptions = checked
        if checked:
            self.link_checkbox.setText("🔗 Linked")
            if self.selected_item_id is not None:
                if self.desc_edit.toPlainText() != self.purchase_desc_edit.toPlainText():
                    self._syncing_descriptions = True
                    self.purchase_desc_edit.setPlainText(self.desc_edit.toPlainText())
                    self._syncing_descriptions = False
        else:
            self.link_checkbox.setText("🔗 Link Descriptions")
        log_action(f"Link descriptions {'enabled' if checked else 'disabled'}")

    def on_description_text_changed(self):
        if self._syncing_descriptions:
            return
        if self.link_descriptions and not self.purchase_desc_edit.hasFocus():
            self.purchase_desc_edit.setPlainText(self.desc_edit.toPlainText())

    def on_purchase_description_text_changed(self):
        if self._syncing_descriptions:
            return
        if self.link_descriptions and not self.desc_edit.hasFocus():
            self.desc_edit.setPlainText(self.purchase_desc_edit.toPlainText())

    # ---------- Launch Search ----------
    def launch_search(self):
        if not self.selected_item_id:
            return
        cached = self.client.cache.get_item(self.selected_item_id)
        if not cached:
            QMessageBox.warning(self, "Warning", "Item details not available.")
            return

        # Log the entire cached item for debugging
        log_action(f"DEBUG: Cached item for {self.selected_item_id}: {cached}")
        
        item_name = cached.get('name', '')
        brand = cached.get('brand', '').strip()
        
        log_action(f"DEBUG: Item name = '{item_name}', Brand from cache = '{brand}'")
        
        if not item_name:
            return

        # Construct search query
        if brand:
            search_query = f"{item_name} {brand}"
            log_action(f"DEBUG: Using brand in query: '{search_query}'")
        else:
            search_query = item_name
            log_action(f"DEBUG: No brand found, using only item name: '{search_query}'")

        sources = self.config.get("search_sources", {})
        if not any(sources.values()):
            QMessageBox.information(self, "No Sources", "No search sources enabled. Please enable some in Settings -> Search Sources.")
            return

        # Disable button to prevent multiple clicks
        self.launch_search_btn.setEnabled(False)
        self.statusBar().showMessage("🔍 Launching searches...")
        QApplication.processEvents()

        try:
            results = BrowserSearch.search_all_sources(search_query, sources, delay=0.5)
            self.history_manager.add_entry(search_query, sources)
            log_action(f"Launched search for '{search_query}' with sources: {[s for s, e in sources.items() if e]}")
            self.statusBar().showMessage("Searches launched", 3000)
        except Exception as e:
            error_msg = f"Error launching search: {str(e)}"
            self.statusBar().showMessage(f"{error_msg}")
            log_action(error_msg)
            QMessageBox.warning(self, "Search Error", f"Could not open browser:\n{str(e)}")
        finally:
            self.launch_search_btn.setEnabled(True)

    def launch_zoho_books_search(self):
        """Open Zoho Books web app with a search for the selected item."""
        if not self.selected_item_id:
            return

        cached = self.client.cache.get_item(self.selected_item_id)
        if not cached:
            QMessageBox.warning(self, "Warning", "Item details not available.")
            return

        item_name = cached.get('name', '')
        brand = cached.get('brand', '').strip()
        if not item_name:
            return

        # Build search query: item name + brand if available
        search_query = f"{item_name} {brand}" if brand else item_name

        org_id = self.client.org_id
        if not org_id:
            QMessageBox.warning(self, "Error", "Organization ID not configured.")
            return

        # Use the new method from browser_search.py
        from browser_search import BrowserSearch  # already imported at top, but ensure it's there
        success = BrowserSearch.open_zoho_books_search(search_query, org_id)

        # Disable button to prevent multiple clicks
        self.zoho_search_btn.setEnabled(False)
        self.statusBar().showMessage("🔍 Launching searches...")
        QApplication.processEvents()

        if success:
            log_action(f"Opened Zoho Books search for '{search_query}'")
            self.statusBar().showMessage("🔍 Zoho Books search opened", 3000)
        else:
            error_msg = "Failed to open Zoho Books search"
            self.statusBar().showMessage(f"❌ {error_msg}")
            log_action(error_msg)
            QMessageBox.warning(self, "Browser Error", "Could not open Zoho Books in your browser.")

        self.zoho_search_btn.setEnabled(True)

    # ---------- Brand management ----------
    def load_brands(self):
        """Fetch all brands from Zoho and populate combo box."""
        def on_brands_received(brands):
            self.brands_list = brands
            self.brand_combo.clear()
            self.brand_combo.addItems(brands)
            log_action(f"Loaded {len(brands)} brands")

        def on_brands_error(error_msg):
            log_action(f"Failed to load brands: {error_msg}")

        self.brand_fetch_thread = FetchBrandsThread(self.client)
        self.brand_fetch_thread.finished.connect(on_brands_received)
        self.brand_fetch_thread.error.connect(on_brands_error)
        self.brand_fetch_thread.start()

    def update_brand(self):
        """Update the brand for the selected item."""
        if not self.selected_item_id:
            return
        new_brand = self.brand_combo.currentText().strip()
        if not new_brand:
            QMessageBox.warning(self, "Warning", "Brand cannot be empty.")
            return

        self.update_brand_btn.setEnabled(False)
        self.statusBar().showMessage("🔄 Updating brand...")
        log_action(f"Updating brand for item {self.selected_item_id} to '{new_brand}'")

        self.brand_update_thread = BrandUpdateThread(self.client, self.selected_item_id, new_brand)
        self.brand_update_thread.finished.connect(self.on_brand_updated)
        self.brand_update_thread.error.connect(self.on_brand_update_error)
        self.brand_update_thread.start()

    def on_brand_updated(self, data):
        self.update_brand_btn.setEnabled(True)
        # Update cache
        self.client.cache.update_items([data['details']])
        # Update tree row (brand column)
        self.update_tree_item(data['details'])
        # Update combo box with new value (if new, add to list)
        new_brand = data['details'].get('brand', '')
        if new_brand and new_brand not in self.brands_list:
            self.brands_list.append(new_brand)
            self.brands_list.sort()
            self.brand_combo.addItem(new_brand)
        self.brand_combo.setCurrentText(new_brand)
        self.statusBar().showMessage("✅ Brand updated")
        log_action(f"Brand updated to '{new_brand}'")

    def on_brand_update_error(self, error_msg):
        self.update_brand_btn.setEnabled(True)
        self.statusBar().showMessage(f"❌ Error updating brand: {error_msg}")
        log_action(f"Brand update error: {error_msg}")

    # ---------- Data loading and sync ----------
    def load_from_cache(self):
        items = self.client.cache.search_items()
        self.update_tree(items)
        self.load_brands()
        msg = f"✅ {len(items)} items loaded from cache"
        self.statusBar().showMessage(msg)
        log_action(msg)

    def start_background_sync(self):
        if self.sync_in_progress:
            return
        self.sync_in_progress = True
        msg = "🔄 Background sync started..."
        self.statusBar().showMessage(msg)
        log_action(msg)
        self.sync_thread = SyncThread(self.client)
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.error.connect(self.on_sync_error)
        self.sync_thread.start()

    def on_sync_finished(self):
        self.sync_in_progress = False
        items = self.client.cache.search_items()
        self.update_tree(items)
        self.load_brands()
        msg = "✅ Sync completed"
        self.statusBar().showMessage(msg)
        log_action(msg)

    def on_sync_error(self, error_msg):
        self.sync_in_progress = False
        msg = f"❌ Sync error: {error_msg}"
        self.statusBar().showMessage(msg)
        log_action(msg)

    def refresh_data(self):
        self.start_background_sync()
        log_action("Manual refresh all requested")

    def auto_sync(self):
        if not self.sync_in_progress:
            log_action("Auto-sync every 5 minutes")
            self.start_background_sync()

    def on_error(self, error_msg):
        self.statusBar().showMessage(f"❌ Error: {error_msg}")
        log_action(f"Error: {error_msg}")
        if hasattr(self, '_saved_link_state') and self._saved_link_state:
            self.link_checkbox.setChecked(True)

    def update_tree(self, items):
        self.tree.clear()
        for item in items:
            tree_item = QTreeWidgetItem([
                item.get('name', ''),
                item.get('sku', ''),
                item.get('brand', ''),
                str(item.get('stock_on_hand', 0)),
                item.get('status', '')
            ])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item.get('item_id'))
            if item.get('status') == 'active':
                tree_item.setBackground(4, QColor(self.active_color))
            else:
                tree_item.setBackground(4, QColor(self.inactive_color))
            self.tree.addTopLevelItem(tree_item)

    def filter_items(self):
        raw_query = self.search_input.text()
        query = raw_query.strip().lower()
        items = self.client.cache.search_items(query)
        self.update_tree(items)

    # ---------- Item selection ----------
    def on_item_selected(self):
        if self.loading_details:
            return

        selected = self.tree.selectedItems()
        if not selected:
            return
        item = selected[0]
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        if item_id == self.selected_item_id:
            return
        self.selected_item_id = item_id

        log_action(f"Selected item: {item.text(0)} (ID: {item_id})")

        self.tree.setEnabled(False)
        self.toggle_btn.setEnabled(False)
        self.refresh_item_btn.setEnabled(False)
        self.launch_search_btn.setVisible(False)
        self.save_desc_btn.setEnabled(False)
        self.loading_details = True
        self.statusBar().showMessage(f"⏳ Loading details for {item.text(0)}...")

        cached = self.client.cache.get_item(item_id)
        if cached:
            self.stock_label.setText(f"Physical: {cached['stock_on_hand']} | Accounting: {cached['available_stock']}")
            self.brand_combo.setCurrentText(cached.get('brand', ''))
            self.brand_combo.setEnabled(not self.lock_checkbox.isChecked())
            self.update_brand_btn.setEnabled(not self.lock_checkbox.isChecked())
            self.qty_label.setText(f"Purchased: {cached['purchased_qty']} units (${cached['purchased_amt']:,.2f})\nSold: {cached['sold_qty']} units (${cached['sold_amt']:,.2f})")
            
            # Temporarily disable linking to avoid recursion
            self._syncing_descriptions = True
            self.desc_edit.setPlainText(cached.get('description', ''))
            self.purchase_desc_edit.setPlainText(cached.get('purchase_description', ''))
            self._syncing_descriptions = False
            
            if cached['status'] == 'active':
                self.toggle_btn.setText("Mark as Inactive")
                self.toggle_btn.setStyleSheet(f"background-color: {self.inactive_color}; color: white; border: none;")
            else:
                self.toggle_btn.setText("Mark as Active")
                self.toggle_btn.setStyleSheet(f"background-color: {self.active_color}; color: white; border: none;")
            self.toggle_btn.setVisible(True)
            self.refresh_item_btn.setVisible(True)
            self.launch_search_btn.setVisible(True)
            self.zoho_search_btn.setVisible(True)
            self.desc_edit.setEnabled(not self.lock_checkbox.isChecked())
            self.purchase_desc_edit.setEnabled(not self.lock_checkbox.isChecked())
            self.save_desc_btn.setEnabled(not self.lock_checkbox.isChecked())
        else:
            self.stock_label.setText("Loading...")
            self.brand_combo.clear()
            self.brand_combo.setEnabled(False)
            self.update_brand_btn.setEnabled(False)
            self.qty_label.setText("")
            self.desc_edit.clear()
            self.purchase_desc_edit.clear()
            self.toggle_btn.setVisible(False)
            self.refresh_item_btn.setVisible(False)
            self.launch_search_btn.setVisible(False)

        self.doc_text.clear()
        self.details_thread = DetailsThread(self.client, item_id)
        self.details_thread.finished.connect(self.display_details)
        self.details_thread.error.connect(self.on_details_error)
        self.details_thread.start()

    def display_details(self, data):
        def get_date(doc):
            if 'last_modified_time' in doc and doc['last_modified_time']:
                return doc['last_modified_time'][:10]
            if 'created_time' in doc and doc['created_time']:
                return doc['created_time'][:10]
            return ''

        details = data['details']
        self.qty_label.setText(f"Purchased: {data['purchased_qty']} units (${data['purchased_amt']:,.2f})\nSold: {data['sold_qty']} units (${data['sold_amt']:,.2f})")

        # Temporarily disable linking to avoid recursion when setting text
        if not self.description_modified:
            self._syncing_descriptions = True
            self.desc_edit.setPlainText(details.get('description', ''))
            self.purchase_desc_edit.setPlainText(details.get('purchase_description', ''))
            self._syncing_descriptions = False

        doc_lines = []
        doc_lines.append("--- SALES ORDERS ---")
        for so in data['sales_orders']:
            date = get_date(so)
            doc_lines.append(f"{so.get('salesorder_number', 'N/A')} [{date}]: {so.get('status', '')}")
        doc_lines.append("\n--- PURCHASE ORDERS ---")
        for po in data['purchase_orders']:
            date = get_date(po)
            doc_lines.append(f"{po.get('purchaseorder_number', 'N/A')} [{date}]: {po.get('status', '')}")
        doc_lines.append("\n--- INVOICES ---")
        for inv in data['invoices']:
            num = inv.get('invoice_number') or inv.get('number', 'N/A')
            date = get_date(inv)
            doc_lines.append(f"{num} [{date}]: {inv.get('status', '')}")
        doc_lines.append("\n--- BILLS ---")
        for bill in data['bills']:
            num = bill.get('bill_number') or bill.get('number', 'N/A')
            date = get_date(bill)
            doc_lines.append(f"{num} [{date}]: {bill.get('status', '')}")
        self.doc_text.setText("\n".join(doc_lines))

        self.tree.setEnabled(True)
        self.toggle_btn.setEnabled(True)
        self.refresh_item_btn.setEnabled(True)
        self.loading_details = False
        msg = f"✅ Details loaded for {details.get('name', '')}"
        self.statusBar().showMessage(msg)
        log_action(msg)

    def on_details_error(self, error_msg):
        self.tree.setEnabled(True)
        self.toggle_btn.setEnabled(True)
        self.refresh_item_btn.setEnabled(True)
        self.loading_details = False
        msg = f"❌ Error loading details: {error_msg}"
        self.statusBar().showMessage(msg)
        log_action(msg)

    # ---------- Refresh current item ----------
    def refresh_current_item(self):
        if not self.selected_item_id:
            return
        self.refresh_item_btn.setEnabled(False)
        msg = "🔄 Refreshing item..."
        self.statusBar().showMessage(msg)
        log_action(msg)

        self._saved_link_state = self.link_descriptions
        if self.link_descriptions:
            self.link_descriptions = False
            self.link_checkbox.setChecked(False)

        self.refresh_thread = DetailsThread(self.client, self.selected_item_id)
        self.refresh_thread.finished.connect(self.on_refresh_finished)
        self.refresh_thread.error.connect(self.on_error)
        self.refresh_thread.start()

    def on_refresh_finished(self, data):
        self.refresh_item_btn.setEnabled(True)
        self.client.cache.update_items([data['details']])
        self.update_tree_item(data['details'])
        self.display_details(data)

        if self._saved_link_state:
            self.link_checkbox.setChecked(True)

        msg = "✅ Item refreshed"
        self.statusBar().showMessage(msg)
        log_action(msg)

    def update_tree_item(self, item_data):
        item_id = item_data.get('item_id')
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == item_id:
                item.setText(0, item_data.get('name', ''))
                item.setText(1, item_data.get('sku', ''))
                item.setText(2, item_data.get('brand', ''))
                item.setText(3, str(item_data.get('stock_on_hand', 0)))
                new_status = item_data.get('status', '')
                item.setText(4, new_status)
                if new_status == 'active':
                    item.setBackground(4, QColor(self.active_color))
                else:
                    item.setBackground(4, QColor(self.inactive_color))
                break

    # ---------- Status toggle ----------
    def toggle_item_status(self):
        if not self.selected_item_id or self.loading_details:
            return

        current_text = self.toggle_btn.text()
        if "Inactive" in current_text:
            new_status_active = False
            confirm_msg = "Are you sure you want to deactivate this item?"
            action = "deactivate"
        else:
            new_status_active = True
            confirm_msg = "Are you sure you want to activate this item?"
            action = "activate"

        reply = QMessageBox.question(self, "Confirm", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            log_action(f"Canceled {action} operation")
            return

        log_action(f"Starting {action} for item ID {self.selected_item_id}")

        self.tree.setEnabled(False)
        self.toggle_btn.setEnabled(False)
        self.refresh_item_btn.setEnabled(False)
        self.statusBar().showMessage("🔄 Updating status...")

        self.status_thread = StatusUpdateThread(self.client, self.selected_item_id, new_status_active)
        self.status_thread.finished.connect(self.on_status_updated)
        self.status_thread.error.connect(self.on_error)
        self.status_thread.start()

    def on_status_updated(self, data):
        self.tree.setEnabled(True)
        self.toggle_btn.setEnabled(True)
        self.refresh_item_btn.setEnabled(True)

        updated_item = data['details']
        self.client.cache.update_items([updated_item])
        self.update_tree_item(updated_item)

        if updated_item['status'] == 'active':
            self.toggle_btn.setText("Mark as Inactive")
            self.toggle_btn.setStyleSheet(f"background-color: {self.inactive_color}; color: white; border: none;")
        else:
            self.toggle_btn.setText("Mark as Active")
            self.toggle_btn.setStyleSheet(f"background-color: {self.active_color}; color: white; border: none;")

        msg = f"✅ Status updated to {updated_item['status']}"
        self.statusBar().showMessage(msg)
        log_action(msg)

    # ---------- Description lock and editing ----------
    def toggle_description_lock(self, checked):
        if not checked:
            reply = QMessageBox.warning(self, "Warning",
                                        "You are about to unlock the descriptions for editing.\n"
                                        "Changes will not be saved until you click 'Save Descriptions'.\n"
                                        "Proceed?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.lock_checkbox.setChecked(True)
                return
            self.desc_edit.setEnabled(True)
            self.purchase_desc_edit.setEnabled(True)
            self.brand_combo.setEnabled(True)
            self.update_brand_btn.setEnabled(True)
            self.save_desc_btn.setEnabled(True)
            self.lock_checkbox.setText("🔓 Descriptions Unlocked")
            log_action("Descriptions unlocked")
        else:
            self.desc_edit.setEnabled(False)
            self.purchase_desc_edit.setEnabled(False)
            self.brand_combo.setEnabled(False)
            self.update_brand_btn.setEnabled(False)
            self.save_desc_btn.setEnabled(False)
            self.lock_checkbox.setText("🔒 Descriptions Locked")
            self.description_modified = False
            log_action("Descriptions locked")

    def save_descriptions(self):
        if not self.selected_item_id:
            return
        if self.save_cooldown_active:
            log_action("Save blocked by cooldown")
            return
        sales_desc = self.desc_edit.toPlainText().strip()
        purchase_desc = self.purchase_desc_edit.toPlainText().strip()
        self.save_desc_btn.setEnabled(False)
        self.statusBar().showMessage("🔄 Saving descriptions...")
        log_action(f"Saving descriptions for item {self.selected_item_id}")

        self.save_cooldown_active = True
        self.save_cooldown_timer.start(2000)

        self.desc_thread = DescriptionUpdateThread(self.client, self.selected_item_id, sales_desc, purchase_desc)
        self.desc_thread.finished.connect(self.on_descriptions_saved)
        self.desc_thread.error.connect(self.on_error)
        self.desc_thread.start()

    def on_descriptions_saved(self, data):
        self.save_desc_btn.setEnabled(True)
        self.client.cache.update_items([data['details']])
        self.update_tree_item(data['details'])
        # Temporarily disable linking to avoid recursion
        self._syncing_descriptions = True
        self.desc_edit.setPlainText(data['details'].get('description', ''))
        self.purchase_desc_edit.setPlainText(data['details'].get('purchase_description', ''))
        self._syncing_descriptions = False
        self.description_modified = False
        msg = "✅ Descriptions saved"
        self.statusBar().showMessage(msg)
        log_action(msg)

    # ---------- Utility methods ----------
    def open_log_file(self):
        if not os.path.exists(LOG_FILE):
            QMessageBox.information(self, "Log", "No activities logged yet.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(LOG_FILE)
            elif sys.platform == "darwin":
                subprocess.run(["open", LOG_FILE])
            else:
                subprocess.run(["xdg-open", LOG_FILE])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open log file:\n{e}")

    def show_about(self):
        QMessageBox.about(self, "About",
                          "Inventory Manager\nVersion 2.0\n\n"
                          "Desktop application for Zoho Books inventory management.\n"
                          "Includes search launcher, history, and brand editing.\n"
                          "and Enter-to-save with cooldown.")

    def closeEvent(self, event):
        if self.sync_timer.isActive():
            self.sync_timer.stop()
        if self.save_cooldown_timer.isActive():
            self.save_cooldown_timer.stop()
        log_action("Application closed")
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Handle secure config
    if not config_exists():
        setup = SetupDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        data = setup.get_data()
        password = setup.get_password()
        save_config(data, password)
    else:
        login = LoginDialog()
        while True:
            if login.exec() != QDialog.DialogCode.Accepted:
                sys.exit(0)
            password = login.get_password()
            try:
                data = load_config(password)
                break
            except Exception:
                QMessageBox.warning(login, "Error", "Incorrect password. Try again.")
                continue

    # Create Zoho client with decrypted credentials
    client = ZohoClient(
        client_id=data['client_id'],
        client_secret=data['client_secret'],
        refresh_token=data['refresh_token'],
        org_id=data['org_id']
    )

    window = InventoryApp(client)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()