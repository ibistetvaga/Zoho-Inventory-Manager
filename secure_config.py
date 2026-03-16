"""Secure storage for Zoho credentials using password-based encryption."""

import os
import json
import base64
import platform
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from paths import get_app_data_dir, ensure_app_dir

logger = logging.getLogger(__name__)

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

CONFIG_FILE = os.path.join(get_app_data_dir(), "secure_config.dat")

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

def decrypt_data(encrypted_data: bytes, password: str) -> dict:
    """Decrypt data with password. Raises exception if wrong password."""
    salt = encrypted_data[:16]
    encrypted = encrypted_data[16:]
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted)
    return json.loads(decrypted.decode())

def save_config(data: dict, password: str):
    """Save encrypted config to file. Creates directory if needed."""
    ensure_app_dir()
    encrypted = encrypt_data(data, password)
    with open(CONFIG_FILE, "wb") as f:
        f.write(encrypted)

def load_config(password: str) -> dict:
    """Load and decrypt config from file."""
    with open(CONFIG_FILE, "rb") as f:
        encrypted = f.read()
    return decrypt_data(encrypted, password)

def config_exists() -> bool:
    """Check if config file exists."""
    return os.path.exists(CONFIG_FILE)