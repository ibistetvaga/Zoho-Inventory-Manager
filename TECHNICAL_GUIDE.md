# Technical Programming Guide: Zoho Inventory Analyst Pro

A comprehensive guide to understanding, modifying, and extending this application.

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Understanding Each File](#understanding-each-file)
   - [main.py - The GUI Application](#mainpy---the-gui-application)
   - [zoho_api.py - The API and Cache Layer](#zohopy---the-api-and-cache-layer)
   - [browser_search.py - Web Search Integration](#browser_searchpy---web-search-integration)
   - [history_manager.py - Search History Management](#history_managerpy---search-history-management)
   - [config_manager.py - Configuration Management](#config_managerpy---configuration-management)
   - [threads.py - Background Thread Classes](#threadspy---background-thread-classes)
   - [dialogs.py - Application Dialogs](#dialogspy---application-dialogs)
   - [secure_config.py - Secure Credential Storage](#secure_configpy---secure-credential-storage)
   - [utils.py - Utilities and Constants](#utilspy---utilities-and-constants)
   - [paths.py - Path Management](#pathspy---path-management)
   - [extagnant.py - Find Items Without Documents](#extagnantpy---find-items-without-documents)
   - [mark_inactive.py - Batch Mark Items Inactive](#mark_inactivepy---batch-mark-items-inactive)
   - [one-time.py - OAuth Token Exchange](#one-timepy---oauth-token-exchange)
5. [Core Concepts Explained](#core-concepts-explained)
   - [PyQt6 GUI Programming](#pyqt6-gui-programming)
   - [Threading with PyQt6](#threading-with-pyqt6)
   - [SQLite Database](#sqlite-database)
   - [REST API Integration](#rest-api-integration)
   - [OAuth2 Authentication](#oauth2-authentication)
   - [Password-based Encryption](#password-based-encryption)
6. [How to Modify the App](#how-to-modify-the-app)
   - [Adding a New Feature](#adding-a-new-feature)
   - [Changing the UI](#changing-the-ui)
   - [Adding New API Endpoints](#adding-new-api-endpoints)
   - [Adding New Search Sources](#adding-new-search-sources)
7. [Creating Similar Apps](#creating-similar-apps)
8. [Debugging Tips](#debugging-tips)
9. [Next Steps for Learning](#next-steps-for-learning)

---

## Overview

This application is a **desktop GUI tool** that connects to **Zoho Books** (an online accounting/inventory management system) and allows you to:

- View all inventory items in an interactive table
- Search and filter items by name, SKU, or brand
- View detailed information about each item (sales, purchases, invoices)
- Activate/deactivate items
- Edit product descriptions (sales and purchase)
- Edit product brands
- Lock descriptions to prevent accidental edits
- Link sales and purchase descriptions for automatic sync
- Launch web searches for products across multiple suppliers
- Track search history
- Identify items without any documents (orphan items)
- Batch mark items as inactive
- Protect the application with a password

The app is built with **Python** and uses:
- **PyQt6** for the graphical interface
- **SQLite** for local data caching
- **requests** library for API communication
- **PyQt6 Signals** for background operations
- **cryptography** library for secure credential storage
- **python-dotenv** for environment variable management

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| GUI Framework | PyQt6 | Desktop user interface |
| HTTP Client | requests | API communication |
| Database | SQLite3 (built-in) | Local data caching |
| Authentication | OAuth2 | Secure API access |
| Environment Variables | python-dotenv | Secure credential storage |
| Threading | QThread (PyQt6) | Background operations |
| Encryption | cryptography | Password-based encryption |

---

## Project Structure

```
zoho_inventory_app/
├── main.py               # GUI application (PyQt6)
├── zoho_api.py           # API client + SQLite cache
├── browser_search.py     # Web search integration
├── history_manager.py    # Search history management
├── config_manager.py    # Configuration management
├── threads.py           # QThread subclasses for background operations
├── dialogs.py           # Dialog windows (search sources, history, login, setup)
├── secure_config.py     # Secure credential storage with encryption
├── utils.py             # Utility functions and theme constants
├── paths.py             # Platform-specific path management
├── extagnant.py         # Find items without documents
├── mark_inactive.py     # Batch mark items as inactive
├── one-time.py          # OAuth token exchange script
├── config.json          # Application settings (auto-created)
├── activity.log         # Activity log (auto-created)
├── .env                 # Credentials (you must create)
├── .gitignore           # Git ignore rules
├── inventory.db         # Main cache (auto-created)
├── inventory_full.db    # Full database (auto-created)
├── README.md            # User documentation (Spanish)
└── TECHNICAL_GUIDE.md   # This file
```

---

## Understanding Each File

### main.py - The GUI Application

This file contains the **InventoryApp** class that creates the desktop interface using PyQt6. Let's break it down:

#### Key Components:

**1. Imports and Setup**
```python
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
```

- `PyQt6.QtWidgets`: UI components (windows, buttons, tree widgets)
- `PyQt6.QtCore`: Core functionality (threads, signals, timers)
- `PyQt6.QtGui`: Fonts, colors, actions
- `ZohoClient`: API class from zoho_api.py
- `BrowserSearch`: Web search class
- `HistoryManager`: Search history management
- `ConfigManager`: Configuration management
- `threads`: Various QThread subclasses for background operations
- `dialogs`: Various dialog windows
- `secure_config`: Secure credential storage

**2. Theme Definitions**

The app supports three themes defined in utils.py:
```python
# Cool Pastel Theme
COOL_BG = "#f4f7f9"
COOL_CARD = "#ffffff"
COOL_TEXT = "#2c3e50"

# Warm Pastel Theme
WARM_BG = "#fff2e6"
WARM_CARD = "#ffffff"
WARM_TEXT = "#5e4b3c"

# Dark Theme
DARK_BG = "#1a252f"
DARK_CARD = "#243441"
DARK_TEXT = "#e1e8ed"
```

**3. The InventoryApp Class**

```python
class InventoryApp(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client  # Create API client
        self.config = ConfigManager.load()
        self.current_theme = self.config.get("theme", "dark")
        self.history_manager = HistoryManager()
        self.selected_item_id = None
        self.link_descriptions = False
        
        # Build the UI
        self.create_menu()
        self.setup_ui()
        self.apply_theme(self.current_theme)
        
        # Load data
        self.load_from_cache()
        self.start_background_sync()
        
        # Auto-sync timer (5 minutes)
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.auto_sync)
        self.sync_timer.start(300000)
```

**4. The User Interface Layout**

```
+------------------------------------------------------------------+
| Menu Bar: File | Settings | View | Help                            |
+------------------------------------------------------------------+
| [Search Bar: "Search by name or SKU..."] [Lock] [Link]          |
+------------------------------------------------------------------+
|                                | Stock Info                       |
|  Item List (TreeWidget)        | Brand: ...                      |
|  +----------+---------+------+  | Purchased: X units ($Y)        |
|  | Name     | SKU    |Stock |  | Sold: X units ($Y)               |
|  +----------+---------+------+  |                                 |
|  | Item1    | ABC123 | 50   |  | Sales Description:              |
|  | Item2    | DEF456 | 30   |  | [________________]               |
|  | Item3    | GHI789 | 0    |  |                                 |
|  +----------+---------+------+  | Purchase Description:          |
|                                | [________________]              |
|                                | [Save Descriptions]             |
|                                | [Mark as Inactive]              |
|                                | [Refresh Item]                  |
|                                | [Launch Search]                 |
|                                | -------------------------------- |
|                                | Documents:                       |
|                                | Sales Orders...                 |
|                                | Purchase Orders...              |
|                                | Invoices...                     |
|                                | Bills...                        |
+------------------------------------------------------------------+
| Status: Ready                                                    |
+------------------------------------------------------------------+
```

**5. Key Methods**

| Method | Purpose |
|--------|---------|
| `load_from_cache()` | Load data from SQLite database |
| `start_background_sync()` | Start background thread to sync with Zoho |
| `refresh_data()` | Manual refresh button - syncs with Zoho |
| `update_tree()` | Update visible list of items |
| `filter_items()` | Called when typing in search bar |
| `on_item_selected()` | Triggered when clicking an item |
| `display_details()` | Show item details in right panel |
| `toggle_item_status()` | Activate/deactivate an item |
| `save_descriptions()` | Save edited descriptions to Zoho |
| `update_brand()` | Update brand for an item |
| `launch_search()` | Open web searches for selected item |
| `apply_theme()` | Apply color theme to UI |

**6. Threading with QThread**

The app uses QThread subclasses for background operations to keep the UI responsive:

- `SyncThread`: Syncs all items from Zoho
- `DetailsThread`: Fetches item details
- `StatusUpdateThread`: Activates/deactivates items
- `DescriptionUpdateThread`: Saves description changes
- `BrandUpdateThread`: Updates item brand
- `FetchBrandsThread`: Fetches all brands

**7. Auto-Sync Timer**

The app includes a timer that automatically syncs data every 5 minutes:
```python
self.sync_timer = QTimer()
self.sync_timer.timeout.connect(self.auto_sync)
self.sync_timer.start(300000)  # 5 minutes in milliseconds
```

---

### zoho_api.py - The API and Cache Layer

This file contains two main classes:

#### 1. LocalCache Class (SQLite Database)

Handles local data storage using SQLite:

```python
class LocalCache:
    DB_PATH = os.path.join(get_app_data_dir(), "inventory.db")
    
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        """Create database tables"""
        with self.get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sku TEXT,
                    stock_on_hand REAL DEFAULT 0,
                    available_stock REAL DEFAULT 0,
                    status TEXT,
                    purchased_qty REAL DEFAULT 0,
                    purchased_amt REAL DEFAULT 0,
                    sold_qty REAL DEFAULT 0,
                    sold_amt REAL DEFAULT 0,
                    description TEXT,
                    purchase_description TEXT,
                    brand TEXT,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
```

**LocalCache Methods:**

| Method | Purpose |
|--------|---------|
| `init_db()` | Create tables if they don't exist |
| `update_items(items)` | Insert or update multiple items |
| `search_items(query)` | Search by name or SKU |
| `get_item(item_id)` | Get a single item |
| `clear_all()` | Delete all items |

#### 2. ZohoClient Class (API Communication)

Handles all communication with Zoho Books API:

```python
class ZohoClient:
    TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
    BASE_URL = "https://www.zohoapis.com/books/v3"
    
    def __init__(self, client_id=None, client_secret=None, refresh_token=None, org_id=None):
        self.org_id = org_id or os.getenv("ZOHO_ORG_ID")
        self.client_id = client_id or os.getenv("ZOHO_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ZOHO_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.getenv("ZOHO_REFRESH_TOKEN")
        
        self.session = requests.Session()
        self.access_token = None
        self.token_expiry = None
        self._refresh_access_token()
        
        self.cache = LocalCache()
```

**Token Management (OAuth2):**

```python
def _refresh_access_token(self):
    """Exchange refresh token for a new access token"""
    params = {
        "refresh_token": self.refresh_token,
        "client_id": self.client_id,
        "client_secret": self.client_secret,
        "grant_type": "refresh_token"
    }
    response = self.session.post(self.TOKEN_URL, params=params)
    data = response.json()
    self.access_token = data["access_token"]
    self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))

def _ensure_valid_token(self):
    """Check if token is valid, refresh if needed"""
    if not self.access_token or not self.token_expiry or \
       datetime.now() >= self.token_expiry - timedelta(minutes=5):
        self._refresh_access_token()
```

**Key ZohoClient Methods:**

| Method | Purpose | API Endpoint |
|--------|---------|--------------|
| `get_all_items()` | Fetch all inventory items | `GET /items` |
| `sync_all_items()` | Force sync from API to cache | `GET /items` |
| `get_item_details(id)` | Get details + transactions | `GET /items/{id}`, `GET /salesorders`, etc. |
| `update_item_status(id, activate)` | Activate/deactivate item | `POST /items/{id}/active` or `/inactive` |
| `update_item_descriptions(id, sales, purchase)` | Update descriptions | `PUT /items/{id}` |
| `update_item_brand(id, brand)` | Update item brand | `PUT /items/{id}` |
| `get_all_brands()` | Get list of all unique brands | Internal from cache |

**Parallel API Calls:**

```python
def get_item_details(self, item_id):
    """Fetch item details and all related documents in parallel"""
    
    endpoints = ["salesorders", "purchaseorders", "invoices", "bills"]
    results = {ep: [] for ep in endpoints}
    
    # Use ThreadPoolExecutor to fetch all at once
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ep = {}
        for ep in endpoints:
            params = {"item_id": item_id}
            future = executor.submit(self._request, "GET", ep, params=params)
            future_to_ep[future] = ep
        
        for future in as_completed(future_to_ep):
            ep = future_to_ep[future]
            try:
                data = future.result()
                results[ep] = data.get(ep, [])
            except Exception as e:
                logger.error(f"Failed to fetch {ep}: {e}")
    
    return {
        "details": item_info,
        "sales_orders": results["salesorders"],
        "purchase_orders": results["purchaseorders"],
        "invoices": results["invoices"],
        "bills": results["bills"],
        "purchased_qty": purchased_qty,
        "purchased_amt": purchased_amt,
        "sold_qty": sold_qty,
        "sold_amt": sold_amt
    }
```

---

### browser_search.py - Web Search Integration

Handles opening search queries in the default browser:

```python
class BrowserSearch:
    URLS: ClassVar[dict[str, str]] = {
        'google': "https://www.google.com/search?q={query}",
        'google_ai': "https://www.google.com/search?q={query}&udm=50",
        'zoro': "https://www.zoro.com/search?q={query}",
        'grainger': "https://www.grainger.com/search?searchQuery={query}&searchBar=true",
        'ebay': "https://www.ebay.com/sch/i.html?_nkw={query}",
        'amazon': "https://www.amazon.com/s?k={query}",
        'eaton': "https://www.eaton.com/us/en-us/site-search.html.searchTerm${query}.tabs$all.html",
        'tequipment': "https://www.tequipment.net/search/?F_Keyword={query}",
        'lowes': "https://www.lowes.com/search?searchTerm={query}",
    }
    
    DISPLAY_NAMES: ClassVar[dict[str, str]] = {
        'google': 'Google Search',
        'google_ai': 'Google AI Search',
        'zoro': 'Zoro',
        'grainger': 'Grainger',
        'ebay': 'eBay',
        'amazon': 'Amazon',
        'eaton': 'Eaton',
        'tequipment': 'Tequipment',
        'lowes': "Lowe's",
    }
    
    @classmethod
    def search_all_sources(cls, query: str, selected_sources: dict, delay: float = 0.5) -> dict:
        """Search across all selected sources with a delay between each"""
        results = {}
        for source, enabled in selected_sources.items():
            if enabled:
                success = cls.open_search(source, query)
                results[source] = {'success': success, 'query': query}
                if delay > 0:
                    time.sleep(delay)  # small pause between launches
        return results
```

---

### history_manager.py - Search History Management

Manages search history with JSON storage:

```python
class HistoryManager:
    SCHEMA_VERSION = 1
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.app_data_dir = self._get_app_data_dir()
        self.data_dir = os.path.join(self.app_data_dir, "data")
        self.history_file = os.path.join(self.data_dir, "search_history.json")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.history = []
        self.load_history()
    
    def add_entry(self, query: str, sources: Dict[str, bool]) -> None:
        """Add a new search entry to history"""
        entry = {
            'query': query,
            'sources': {k: v for k, v in sources.items() if v},
            'timestamp': datetime.now().isoformat(),
            'display_time': self._format_timestamp(datetime.now())
        }
        # Remove duplicates and add new entry
        self.history = [e for e in self.history if not (e['query'] == query and e['sources'] == sources)]
        self.history.insert(0, entry)
        self.history = self.history[:self.max_history]
        self.save_history()
```

**Key Features:**
- JSON-based storage with atomic writes
- Automatic backup creation (keeps last 3 backups)
- Backup restoration on corruption
- Export/import functionality
- Platform-appropriate data directory
- Schema versioning for future migrations

---

### config_manager.py - Configuration Management

Handles loading and saving application configuration:

```python
class ConfigManager:
    CONFIG_FILE = os.path.join(get_app_data_dir(), "config.json")
    
    @classmethod
    def load(cls):
        """Load config from JSON file. Returns dict with defaults."""
        default_sources = {source: (source == 'google') for source in BrowserSearch.get_source_names()}
        default = {
            "search_sources": default_sources,
            "theme": "dark"
        }
        # Load from file if exists, otherwise return defaults
```

---

### threads.py - Background Thread Classes

QThread subclasses for background operations:

```python
class SyncThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

class DetailsThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class StatusUpdateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class DescriptionUpdateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class BrandUpdateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class FetchBrandsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
```

---

### dialogs.py - Application Dialogs

Contains various dialog windows:

1. **SearchSourcesDialog**: Configure which search engines to use
2. **SearchHistoryDialog**: View and rerun previous searches
3. **LoginDialog**: Password-protected login
4. **SetupDialog**: First-time setup with Zoho credentials and password
5. **ChangePasswordDialog**: Change application password

Each dialog validates input and provides feedback to users.

---

### secure_config.py - Secure Credential Storage

Provides password-based encryption for storing Zoho credentials:

```python
def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet key from password and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_data(data: dict, password: str) -> bytes:
    """Encrypt a dictionary with password. Returns salt + encrypted data."""
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    json_data = json.dumps(data).encode()
    encrypted = fernet.encrypt(json_data)
    return salt + encrypted
```

**Key Features:**
- Uses PBKDF2 with 100,000 iterations for key derivation
- Fernet symmetric encryption (AES-128-CBC with HMAC)
- Random salt for each encryption
- Platform-appropriate storage location

---

### utils.py - Utilities and Constants

Contains utility functions and theme color constants:

```python
# Log file path
LOG_FILE = os.path.join(get_app_data_dir(), "activity.log")

# Cool Pastel Theme
COOL_BG = "#f4f7f9"
COOL_CARD = "#ffffff"
COOL_TEXT = "#2c3e50"

# Warm Pastel Theme
WARM_BG = "#fff2e6"
WARM_CARD = "#ffffff"
WARM_TEXT = "#5e4b3c"

# Dark Theme
DARK_BG = "#1a252f"
DARK_CARD = "#243441"
DARK_TEXT = "#e1e8ed"

# Accent colors
ACCENT_MINT = "#b2d8d8"
ACCENT_PEACH = "#ffd3b6"
ACCENT_SALMON = "#ffaaa5"
ACCENT_LAVENDER = "#c3bedd"

def log_action(message: str):
    """Write a timestamped message to the log file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")
```

---

### paths.py - Path Management

Platform-specific path management:

```python
APP_NAME = "InventoryManager"

def get_app_data_dir():
    """Return platform-specific application data directory."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, APP_NAME)
    elif system == "Darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, APP_NAME)
    else:  # Linux and others
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(base, APP_NAME)
```

---

### extagnant.py - Find Items Without Documents

Script to find items that never appear in any document and export to Excel:

```python
# Key functions:
def process_document_type(client, doc_type, id_field, number_field):
    """Process all documents of a given type"""
    # Fetches all salesorders, purchaseorders, invoices, bills
    # Stores document-item relationships in SQLite

def main():
    # Step 1: Fetch all items and store in database
    items = client.get_all_items(force_refresh=True)
    
    # Step 2: Process each document type
    for doc_type, id_field, number_field in DOC_TYPES:
        process_document_type(client, doc_type, id_field, number_field)
    
    # Step 3: Find items with no documents
    c.execute("""
        SELECT i.item_id, i.name, i.status, i.purchased_qty, i.sold_qty
        FROM items i
        LEFT JOIN document_items di ON i.item_id = di.item_id
        WHERE di.item_id IS NULL
    """)
    
    # Step 4: Export to Excel/JSON
    df.to_excel(args.output, index=False)
```

**Usage:**
```bash
python extagnant.py --reset        # Reset and start fresh
python extagnant.py -o output.xlsx # Custom output
```

---

### mark_inactive.py - Batch Mark Items Inactive

Script to mark items as inactive based on JSON output:

```python
def main():
    # Load items from JSON
    with open(input_path, 'r') as f:
        items = json.load(f)
    
    # Process each item
    for item in items_to_process:
        client.update_item_status(item_id, activate=False)
        time.sleep(REQUEST_DELAY)  # Rate limiting
```

**Usage:**
```bash
python mark_inactive.py --input items_sin_documentos.json
python mark_inactive.py --dry-run    # Preview without changes
python mark_inactive.py --skip-existing  # Skip already inactive
```

---

### one-time.py - OAuth Token Exchange

This is a utility script to get your initial refresh token:

```python
# Replace with the authorization code from Zoho Console
GRANT_CODE = 'your_authorization_code_here'

url = "https://accounts.zoho.com/oauth/v2/token"

payload = {
    "code": GRANT_CODE,
    "client_id": os.getenv("ZOHO_CLIENT_ID"),
    "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
    "grant_type": "authorization_code"
}

response = requests.post(url, params=payload)
data = response.json()

if "refresh_token" in data:
    print(f"Refresh Token: {data['refresh_token']}")
```

---

## Core Concepts Explained

### PyQt6 GUI Programming

PyQt6 is a comprehensive GUI framework. Key concepts:

**1. Widget Hierarchy:**
```
QMainWindow
├── QMenuBar
├── QWidget (central)
│   └── QHBoxLayout
│       ├── QSplitter
│       │   ├── QWidget (left panel)
│       │   │   └── QVBoxLayout
│       │   │       ├── QLineEdit (search)
│       │   │       └── QTreeWidget (item list)
│       │   └── QWidget (right panel)
│       │       └── QVBoxLayout
│       │           ├── QLabel (stock info)
│       │           ├── QTextEdit (descriptions)
│       │           └── QPushButton (actions)
└── QStatusBar
```

**2. Common Widgets:**

| Widget | Purpose |
|--------|---------|
| `QMainWindow` | Main application window |
| `QWidget` | Container for grouping widgets |
| `QPushButton` | Clickable button |
| `QLineEdit` | Single-line text input |
| `QTextEdit` | Multi-line text area |
| `QTreeWidget` | Table/tree view |
| `QLabel` | Text display |
| `QSplitter` | Resizable panels |

**3. Layout Management:**
```python
layout = QVBoxLayout()  # Vertical stacking
layout = QHBoxLayout()  # Horizontal stacking

widget.setLayout(layout)
layout.addWidget(some_widget)
layout.addLayout(nested_layout)
```

**4. Signals and Slots:**
```python
# Connect button click to function
button.clicked.connect(self.handle_click)

# Connect item selection to handler
tree.itemSelectionChanged.connect(self.on_item_selected)

# Custom signals
class MyThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
```

---

### Threading with PyQt6

PyQt6 uses QThread for background operations:

```python
class MyThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, client):
        super().__init__()
        self.client = client
    
    def run(self):
        try:
            result = self.client.do_work()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

# Usage
self.thread = MyThread(self.client)
self.thread.finished.connect(self.on_complete)
self.thread.error.connect(self.on_error)
self.thread.start()
```

**Why QThread?**
- Thread-safe communication via signals
- Proper cleanup when app closes
- Integration with Qt event loop

---

### SQLite Database

SQLite is a lightweight, file-based database:

```python
import sqlite3

# Connect to database
conn = sqlite3.connect("inventory.db")
conn.row_factory = sqlite3.Row  # Access columns by name

# Execute SQL
cursor = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%test%',))
results = cursor.fetchall()

# Access by column name
for row in results:
    print(row['name'], row['sku'])

conn.close()
```

**With Context Manager:**
```python
with sqlite3.connect("inventory.db") as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM items")
    results = cursor.fetchall()
# Connection automatically closed
```

---

### REST API Integration

REST APIs work with HTTP methods:

| Method | Purpose | Example |
|--------|---------|---------|
| `GET` | Retrieve data | Get all items |
| `POST` | Create data | Create new item |
| `PUT` | Update data | Update item description |
| `DELETE` | Remove data | Delete an item |

**API Request Pattern:**
```python
def _request(self, method, endpoint, **kwargs):
    """Make an authenticated API request."""
    self._ensure_valid_token()
    
    url = f"{self.BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {self.access_token}",
        "Content-Type": "application/json"
    }
    
    kwargs.setdefault('headers', headers)
    response = self.session.request(method, url, **kwargs)
    
    if response.status_code == 401:
        # Token expired, refresh and retry
        self._refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {self.access_token}"
        response = self.session.request(method, url, **kwargs)
    
    response.raise_for_status()
    return response.json()
```

---

### OAuth2 Authentication

OAuth2 is the standard for secure API access:

1. **Authorization Code Flow** (used for initial setup):
   - User visits Zoho's authorization page
   - User grants permission
   - Zoho returns an authorization code
   - Your app exchanges the code for a refresh token

2. **Refresh Token Flow** (used by the app):
   - Access tokens expire (typically 1 hour)
   - App uses refresh token to get a new access token
   - No user interaction needed

**Token Refresh:**
```python
def _refresh_access_token(self):
    params = {
        "refresh_token": self.refresh_token,
        "client_id": self.client_id,
        "client_secret": self.client_secret,
        "grant_type": "refresh_token"
    }
    response = self.session.post(self.TOKEN_URL, params=params)
    data = response.json()
    self.access_token = data["access_token"]
    self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
```

---

### Password-based Encryption

The app uses strong password-based encryption for storing credentials:

**Key Derivation (PBKDF2):**
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,  # Random 16 bytes
    iterations=100000,  # High iteration count for security
)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
```

**Encryption (Fernet):**
```python
from cryptography.fernet import Fernet

fernet = Fernet(key)
encrypted = fernet.encrypt(data)
```

**Why This Approach?**
- PBKDF2 slows down brute-force attacks
- Random salt ensures different encryptions for same data
- Fernet provides authenticated encryption
- 100,000 iterations makes it computationally expensive to crack

---

## How to Modify the App

### Adding a New Feature

1. **Plan the feature**: What should it do? What UI elements needed?
2. **Add to the data layer** (if needed): Update `zoho_api.py` to fetch/store data
3. **Add to the UI**: Update `main.py` to display the feature
4. **Test thoroughly**: Make sure it works with all themes and edge cases

Example: Adding a new button to export items:
```python
# In main.py, add button
self.export_btn = QPushButton("Export to CSV")
self.export_btn.clicked.connect(self.export_items)

# Add method
def export_items(self):
    import csv
    items = self.client.cache.search_items(self.search_box.text())
    with open('items.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'sku', 'stock_on_hand'])
        writer.writeheader()
        writer.writerows(items)
```

---

### Changing the UI

The UI is built in the `setup_ui()` method of `InventoryApp`. Key areas:

- **Left panel**: Item list with search
- **Right panel**: Item details, descriptions, actions
- **Menu bar**: File, Settings, View, Help menus

To modify colors, edit the constants in `utils.py` and update `apply_theme()` in `main.py`.

---

### Adding New API Endpoints

To add a new Zoho Books API endpoint:

1. Add method to `ZohoClient` in `zoho_api.py`:
```python
def get_item_images(self, item_id):
    """Get item images from Zoho."""
    return self._request("GET", f"items/{item_id}/images")
```

2. Add a thread class in `threads.py` if needed
3. Add UI elements to display the new data

---

### Adding New Search Sources

To add a new search source:

1. Update `URLS` dictionary in `browser_search.py`:
```python
'new_source': "https://www.newsource.com/search?q={query}",
```

2. Update `DISPLAY_NAMES`:
```python
'new_source': 'New Source',
```

3. The new source will automatically appear in settings

---

## Creating Similar Apps

To create a similar app for another API:

1. **Identify the API**: Find documentation (Zoho, QuickBooks, Xero, etc.)
2. **Set up OAuth**: Get credentials and understand the auth flow
3. **Create the data layer**: Build API client and cache
4. **Build the UI**: Use PyQt6 to create the interface
5. **Add features**: Search, filters, details, actions
6. **Test thoroughly**: Test with real data and edge cases

**Key Files to Reuse:**
- `browser_search.py` - Can be adapted for other search engines
- `threads.py` - QThread pattern works for any API
- `config_manager.py` - Can be adapted for other settings
- `utils.py` - Theme system can be reused
- `paths.py` - Cross-platform path handling

---

## Debugging Tips

1. **Enable logging**: Check `activity.log` for errors
2. **Use print statements**: Add `print()` statements to trace execution
3. **Check API responses**: Print raw API responses to see the data structure
4. **Test with Postman**: Verify API calls work outside the app
5. **Database inspection**: Use SQLite browser to inspect `inventory.db`
6. **Theme testing**: Test all three themes when making UI changes

**Common Issues:**

| Issue | Solution |
|-------|----------|
| Token expired | Run `one-time.py` to get new refresh token |
| API rate limits | Wait and retry, or reduce sync frequency |
| Empty search results | Check the search query and database |
| UI freezes | Ensure API calls run in background threads |
| Password forgotten | Delete `secure_config.dat` and run setup again |

---

## Next Steps for Learning

To deepen your understanding of this application and similar projects:

1. **Learn PyQt6**: Read the official PyQt documentation and tutorials
2. **Understand REST APIs**: Learn about HTTP methods, authentication, rate limiting
3. **Study SQLite**: Learn about indexes, queries, and database design
4. **Explore cryptography**: Understand encryption, hashing, and secure storage
5. **Practice threading**: Learn about concurrent programming in Python
6. **Read Zoho API docs**: Understand all available endpoints and features

**Recommended Resources:**
- PyQt6 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- Zoho Books API: https://www.zoho.com/books/api/v3/
- Python SQLite: https://docs.python.org/3/library/sqlite3.html
- Cryptography library: https://cryptography.io/

---

*This guide was written for Zoho Inventory Analyst Pro version 1.0*
