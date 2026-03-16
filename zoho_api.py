import requests
import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import time
from paths import get_app_data_dir, ensure_app_dir
REQUEST_DELAY = 0.6  # 100 requests per minute

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LocalCache:
    """SQLite local cache for items."""
    DB_PATH = os.path.join(get_app_data_dir(), "inventory.db")

    def __init__(self):
        ensure_app_dir()  # make sure directory exists
        self.init_db()  # ensure DB is initialized

    @contextmanager
    def get_db(self):
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Create tables if they don't exist, add new columns if needed."""
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
                    purchase_description TEXT,  -- <-- NEW column for purchase description
                    brand TEXT,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Check for missing columns and add them
            c = conn.execute("PRAGMA table_info(items)")
            columns = [col[1] for col in c.fetchall()]
            if 'description' not in columns:
                conn.execute("ALTER TABLE items ADD COLUMN description TEXT")
            if 'purchase_description' not in columns:   # <-- NEW
                conn.execute("ALTER TABLE items ADD COLUMN purchase_description TEXT")
            if 'brand' not in columns:
                conn.execute("ALTER TABLE items ADD COLUMN brand TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_sku ON items(sku)")
            conn.commit()

    def update_items(self, items: List[Dict]):
        """Insert or replace multiple items."""
        with self.get_db() as conn:
            for item in items:
                # Extract brand: first try top-level 'brand' field, then custom fields
                brand = item.get('brand', '')
                if not brand:
                    custom_fields = item.get('custom_fields', [])
                    for cf in custom_fields:
                        label = cf.get('label', '')
                        if label.lower() in ('brand', 'marca'):
                            brand = cf.get('value', '')
                            break

                description = item.get('description', '')
                purchase_description = item.get('purchase_description', '')
                conn.execute("""
                    INSERT OR REPLACE INTO items
                    (item_id, name, sku, stock_on_hand, available_stock, status,
                    purchased_qty, purchased_amt, sold_qty, sold_amt,
                    description, purchase_description, brand, last_sync)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    item.get('item_id'),
                    item.get('name'),
                    item.get('sku'),
                    item.get('stock_on_hand', 0),
                    item.get('available_stock', 0),
                    item.get('status'),
                    item.get('purchased_quantity', 0),
                    item.get('purchased_amount', 0),
                    item.get('sold_quantity', 0),
                    item.get('sold_amount', 0),
                    description,
                    purchase_description,
                    brand
                ))
            conn.commit()

    def search_items(self, query: str = "") -> List[Dict]:
        """Search items by name or SKU (case-insensitive). Empty query returns all."""
        with self.get_db() as conn:
            if query:
                cur = conn.execute("""
                    SELECT * FROM items
                    WHERE name LIKE ? OR sku LIKE ?
                    ORDER BY name
                """, (f'%{query}%', f'%{query}%'))
            else:
                cur = conn.execute("SELECT * FROM items ORDER BY name")
            return [dict(row) for row in cur.fetchall()]

    def get_item(self, item_id: str) -> Optional[Dict]:
        """Get a single item by ID."""
        with self.get_db() as conn:
            cur = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def clear_all(self):
        """Delete all items (for testing)."""
        with self.get_db() as conn:
            conn.execute("DELETE FROM items")
            conn.commit()


class ZohoClient:
    """Client for Zoho Books API v3."""

    TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
    BASE_URL = "https://www.zohoapis.com/books/v3"

    def __init__(self, client_id=None, client_secret=None, refresh_token=None, org_id=None):
        """Initialize the client with credentials from arguments or environment."""
        self.org_id = org_id or os.getenv("ZOHO_ORG_ID")
        self.client_id = client_id or os.getenv("ZOHO_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ZOHO_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.getenv("ZOHO_REFRESH_TOKEN")

        if not all([self.org_id, self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Missing required Zoho credentials. Please provide them via arguments or .env file.")

        self.session = requests.Session()
        self.access_token = None
        self.token_expiry = None
        self._refresh_access_token()

        # Initialize local cache
        self.cache = LocalCache()

    # ---------- Token management ----------
    def _refresh_access_token(self) -> None:
        params = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        try:
            response = self.session.post(self.TOKEN_URL, params=params)
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
            logger.info("Access token refreshed successfully.")
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise

    def _ensure_valid_token(self) -> None:
        if not self.access_token or not self.token_expiry or datetime.now() >= self.token_expiry - timedelta(minutes=5):
            self._refresh_access_token()

    def _get_headers(self) -> Dict[str, str]:
        self._ensure_valid_token()
        return {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "X-com-zoho-books-organizationid": self.org_id
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                logger.warning("Token expired or invalid, refreshing and retrying...")
                self._refresh_access_token()
                headers = self._get_headers()
                response = self.session.request(method, url, headers=headers, **kwargs)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    # ---------- Item fetching ----------
    def get_all_items(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch all items. If force_refresh is False, tries local cache first.
        Otherwise, fetches from API and updates cache.
        """
        if not force_refresh:
            cached = self.cache.search_items()
            if cached:
                logger.info(f"Loaded {len(cached)} items from SQLite cache.")
                return cached
            logger.info("Cache empty, fetching from API...")

        logger.info("Fetching all items from Zoho API (this may take a while)...")
        all_items = []
        page = 1
        has_more = True

        while has_more:
            # <-- NEW: include_custom_fields to get brand in list response
            params = {"page": page, "include_custom_fields": "true"}
            data = self._request("GET", "items", params=params)
            items = data.get("items", [])
            all_items.extend(items)
            has_more = data.get("page_context", {}).get("has_more_page", False)
            page += 1
            logger.debug(f"Fetched page {page-1}, total items so far: {len(all_items)}")
            time.sleep(REQUEST_DELAY)  # <-- NEW: delay between requests to respect rate limits

        # Update cache
        self.cache.update_items(all_items)
        logger.info(f"Cached {len(all_items)} items in SQLite.")

        return all_items

    def sync_all_items(self) -> None:
        """
        Force a full sync from API to cache (no return, used in background).
        """
        logger.info("Background sync: fetching all items from Zoho...")
        all_items = []
        page = 1
        has_more = True

        while has_more:
            # <-- NEW: include_custom_fields
            params = {"page": page, "include_custom_fields": "true"}
            data = self._request("GET", "items", params=params)
            items = data.get("items", [])
            all_items.extend(items)
            has_more = data.get("page_context", {}).get("has_more_page", False)
            page += 1
            time.sleep(REQUEST_DELAY)

        self.cache.update_items(all_items)
        logger.info(f"Background sync completed. Cached {len(all_items)} items.")

    def get_item_details(self, item_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific item, including its documents.
        All document types are fetched in parallel.
        """
        logger.info(f"Fetching details for item {item_id}")

        # Fetch item details (includes purchase/sales summary)
        item_data = self._request("GET", f"items/{item_id}")
        item_info = item_data.get('item', {})

        purchased_qty = item_info.get('purchased_quantity', 0)
        purchased_amt = item_info.get('purchased_amount', 0)
        sold_qty = item_info.get('sold_quantity', 0)
        sold_amt = item_info.get('sold_amount', 0)

        endpoints = ["salesorders", "purchaseorders", "invoices", "bills"]
        results = {ep: [] for ep in endpoints}

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
                    logger.debug(f"Fetched {len(results[ep])} {ep}")
                except Exception as e:
                    logger.error(f"Failed to fetch {ep} for item {item_id}: {e}")

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

    def update_item_status(self, item_id: str, activate: bool) -> Dict[str, Any]:
        """Activate or deactivate an item using the dedicated endpoints."""
        endpoint = f"items/{item_id}/{'active' if activate else 'inactive'}"
        params = {"organization_id": self.org_id}
        response = self._request("POST", endpoint, params=params)
        return response

    # <-- NEW method to update both descriptions
    def update_item_descriptions(self, item_id: str, sales_desc: str, purchase_desc: str) -> Dict[str, Any]:
        """
        Update both the sales description and purchase description of an item.
        """
        # 1. Fetch current item (needed for fields we must preserve)
        item_data = self._request("GET", f"items/{item_id}")
        current_item = item_data.get('item', {})

        # 2. Allowed updatable fields (based on Zoho API docs)
        allowed_fields = [
            'name', 'sku', 'status', 'rate', 'unit',
            'product_type', 'tax_id', 'purchase_rate', 
            'purchase_tax_id', 'preferred_vendor_id', 'item_type',
            'inventory_account_id', 'vendor_id', 'reorder_level',
            'initial_stock', 'initial_stock_rate', 'item_tax_preferences',
            'hsn_or_sac', 'sat_item_key_code', 'unitkey_code'
        ]

        # 3. Build payload with allowed fields
        payload = {}
        for field in allowed_fields:
            if field in current_item:
                value = current_item.get(field)
                if value is not None:
                    payload[field] = value

        # 4. Handle custom fields separately (preserve existing ones)
        if 'custom_fields' in current_item:
            payload['custom_fields'] = current_item['custom_fields']

        # 5. Set the new descriptions
        payload['description'] = sales_desc
        payload['purchase_description'] = purchase_desc

        # 6. Remove any forbidden fields just in case
        forbidden = ['item_id', 'created_time', 'last_modified_time', 'created_by',
                    'modified_by', 'purchased_quantity', 'sold_quantity',
                    'purchased_amount', 'sold_amount', 'stock_on_hand',
                    'available_stock', 'tags', 'has_attachment']
        for field in forbidden:
            payload.pop(field, None)

        logger.debug(f"Updating item {item_id} with payload keys: {list(payload.keys())}")

        # 7. Send PUT request
        response = self._request("PUT", f"items/{item_id}", json=payload)
        return response
    
    def get_api_usage(self):
        """
        Fetch current API usage statistics.
        Tries known endpoints and returns a dict with 'used' and 'limit'.
        If unavailable, returns {'api_usage': {'used': 0, 'limit': 0}}.
        """
        # List of possible endpoints (in order of likelihood)
        possible_endpoints = [
            "settings/apiusage",
            "apiusage",
            "organization/apiusage"
        ]

        for endpoint in possible_endpoints:
            try:
                data = self._request("GET", endpoint)
                # Validate response structure
                if 'api_usage' in data:
                    return data
                else:
                    # Maybe the response is directly the usage
                    if 'used' in data and 'limit' in data:
                        return {'api_usage': data}
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")
                continue

        # If all fail, return zeros and log warning
        logger.warning("Could not fetch API usage from any known endpoint.")
        return {'api_usage': {'used': 0, 'limit': 0}}
    
    def get_all_brands(self) -> List[str]:
        """
        Fetch all unique brand values from all items.
        Returns sorted list of brand names.
        """
        # First try to get from cache if available
        all_items = self.cache.search_items()
        if all_items:
            brands = set()
            for item in all_items:
                brand = item.get('brand', '')
                if brand and brand.strip():
                    brands.add(brand.strip())
            if brands:
                return sorted(brands, key=str.lower)

        # If cache not populated or no brands, fetch from API
        items = self.get_all_items(force_refresh=True)
        brands = set()
        for item in items:
            # Check top-level brand field
            brand = item.get('brand', '')
            if brand and brand.strip():
                brands.add(brand.strip())
            # Also check custom fields
            custom_fields = item.get('custom_fields', [])
            for cf in custom_fields:
                label = cf.get('label', '')
                if label.lower() in ('brand', 'marca'):
                    value = cf.get('value', '').strip()
                    if value:
                        brands.add(value)
                    break
        return sorted(brands, key=str.lower)

    def update_item_brand(self, item_id: str, new_brand: str) -> Dict[str, Any]:
        """
        Update the brand field for an item.
        First checks for a top-level 'brand' field, then falls back to custom fields.
        """
        # Fetch current item
        item_data = self._request("GET", f"items/{item_id}")
        current_item = item_data.get('item', {})

        # Log all keys for debugging (remove after confirming)
        logger.info(f"Item keys: {list(current_item.keys())}")

        # Prepare allowed fields (same as in update_item_descriptions)
        allowed_fields = [
            'name', 'sku', 'status', 'rate', 'unit',
            'product_type', 'tax_id', 'purchase_rate',
            'purchase_tax_id', 'preferred_vendor_id', 'item_type',
            'inventory_account_id', 'vendor_id', 'reorder_level',
            'initial_stock', 'initial_stock_rate', 'item_tax_preferences',
            'hsn_or_sac', 'sat_item_key_code', 'unitkey_code'
        ]

        payload = {}
        for field in allowed_fields:
            if field in current_item:
                value = current_item.get(field)
                if value is not None:
                    payload[field] = value

        # Check for top-level "brand" field (standard field)
        if 'brand' in current_item:
            payload['brand'] = new_brand
            logger.info(f"Updating top-level brand field to '{new_brand}'")
        else:
            # Fall back to custom fields
            custom_fields = current_item.get('custom_fields', [])
            logger.info(f"Custom fields for item {item_id}: {custom_fields}")
            brand_updated = False
            for cf in custom_fields:
                label = cf.get('label', '')
                if label.lower() in ('brand', 'marca'):
                    cf['value'] = new_brand
                    brand_updated = True
                    break

            if not brand_updated:
                available_labels = [cf.get('label', '') for cf in custom_fields]
                error_msg = f"Brand field not found. Available top-level keys: {list(current_item.keys())}. Available custom field labels: {available_labels}. Please ensure a field named 'brand' exists in your item."
                logger.error(error_msg)
                raise Exception(error_msg)

            payload['custom_fields'] = custom_fields

        # Remove any forbidden fields
        forbidden = ['item_id', 'created_time', 'last_modified_time', 'created_by',
                    'modified_by', 'purchased_quantity', 'sold_quantity',
                    'purchased_amount', 'sold_amount', 'stock_on_hand',
                    'available_stock', 'tags', 'has_attachment']
        for field in forbidden:
            payload.pop(field, None)

        logger.debug(f"Updating item {item_id} brand to '{new_brand}'")
        response = self._request("PUT", f"items/{item_id}", json=payload)
        return response