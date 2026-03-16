#!/usr/bin/env python3
"""
Script to build a local SQLite database with all items and all documents
(sales orders, purchase orders, invoices, bills) including line items,
then find items that never appear in any document and export to Excel.
Respects Zoho API rate limits (100 requests/minute) and is resumable.

Enhancements:
- Stores purchased_qty and sold_qty for each item to double-check orphans.
- Exports JSON file in addition to Excel/CSV.
- Output includes quantities for manual verification.
"""

import sys
import csv
import json
import time
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime
from zoho_api import ZohoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "inventory_full.db"

# Rate limiting: 0.6 seconds between requests = 100 per minute
REQUEST_DELAY = 0.6

# Document types and their endpoints
DOC_TYPES = [
    ("salesorders", "salesorder_id", "salesorder_number"),
    ("purchaseorders", "purchaseorder_id", "purchaseorder_number"),
    ("invoices", "invoice_id", "invoice_number"),
    ("bills", "bill_id", "bill_number")
]

def init_db():
    """Create tables if they don't exist, adding quantity columns."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Items table now includes purchased_qty and sold_qty
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            item_id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            purchased_qty REAL DEFAULT 0,
            sold_qty REAL DEFAULT 0
        )
    """)
    # Check if columns exist (for old databases) and add them if missing
    c.execute("PRAGMA table_info(items)")
    columns = [col[1] for col in c.fetchall()]
    if 'purchased_qty' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN purchased_qty REAL DEFAULT 0")
    if 'sold_qty' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN sold_qty REAL DEFAULT 0")

    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            doc_type TEXT,
            doc_number TEXT,
            status TEXT,
            date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS document_items (
            doc_id TEXT,
            item_id TEXT,
            PRIMARY KEY (doc_id, item_id),
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            doc_type TEXT,
            doc_id TEXT,
            PRIMARY KEY (doc_type, doc_id)
        )
    """)
    conn.commit()
    conn.close()

def load_processed(doc_type):
    """Return set of processed document IDs for a given type."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT doc_id FROM progress WHERE doc_type = ?", (doc_type,))
    processed = {row[0] for row in c.fetchall()}
    conn.close()
    return processed

def mark_processed(doc_type, doc_id):
    """Mark a document as processed."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO progress (doc_type, doc_id) VALUES (?, ?)", (doc_type, doc_id))
    conn.commit()
    conn.close()

def fetch_all_paginated(client, endpoint, params=None):
    """Fetch all pages of a list endpoint, yielding items."""
    page = 1
    has_more = True
    while has_more:
        p = {"page": page}
        if params:
            p.update(params)
        data = client._request("GET", endpoint, params=p)
        items = data.get(endpoint, [])
        for item in items:
            yield item
        has_more = data.get("page_context", {}).get("has_more_page", False)
        page += 1
        time.sleep(REQUEST_DELAY)  # rate limit for list requests

def fetch_document_details(client, doc_type, doc_id):
    """Fetch full details of a single document."""
    return client._request("GET", f"{doc_type}/{doc_id}")

def process_document_type(client, doc_type, id_field, number_field):
    """Process all documents of a given type."""
    logger.info(f"Processing {doc_type}...")
    processed = load_processed(doc_type)
    total = 0
    new = 0

    for summary in fetch_all_paginated(client, doc_type):
        doc_id = str(summary.get(id_field))
        if not doc_id:
            continue
        total += 1
        if doc_id in processed:
            continue

        # Fetch full details
        try:
            details = fetch_document_details(client, doc_type, doc_id)
            time.sleep(REQUEST_DELAY)  # rate limit for detail request
        except Exception as e:
            logger.error(f"Failed to fetch {doc_type} {doc_id}: {e}")
            continue

        # Extract document info
        doc_number = summary.get(number_field, '')
        status = summary.get('status', '')
        date = summary.get('date', summary.get('created_time', ''))[:10] if summary.get('date') or summary.get('created_time') else ''

        # Insert document
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO documents (doc_id, doc_type, doc_number, status, date)
            VALUES (?, ?, ?, ?, ?)
        """, (doc_id, doc_type, doc_number, status, date))

        # Extract line items
        line_items = details.get(doc_type[:-1], {}).get('line_items', [])  # e.g., salesorder -> salesorders
        if not line_items:
            # Sometimes the details might have line_items at top level
            line_items = details.get('line_items', [])

        items_added = set()
        for li in line_items:
            item_id = str(li.get('item_id'))
            if item_id and item_id != 'None':
                items_added.add(item_id)
                c.execute("INSERT OR IGNORE INTO document_items (doc_id, item_id) VALUES (?, ?)", (doc_id, item_id))

        conn.commit()
        conn.close()

        mark_processed(doc_type, doc_id)
        new += 1

        if new % 10 == 0:
            logger.info(f"Processed {new} new {doc_type} (total {total})")

    logger.info(f"Finished {doc_type}: {new} new, {total} total")

def main():
    parser = argparse.ArgumentParser(
        description="Build local database of items and documents, then find items without any document."
    )
    parser.add_argument("--reset", action="store_true", help="Reset database and start fresh")
    parser.add_argument("--output", "-o", default="items_sin_documentos.xlsx", help="Output Excel file (JSON and CSV will also be created)")
    args = parser.parse_args()

    if args.reset:
        if Path(DB_PATH).exists():
            Path(DB_PATH).unlink()
            logger.info("Database removed.")
        # Also remove progress? Progress is inside DB, so it's gone.

    init_db()

    client = ZohoClient()

    # Step 1: Fetch all items and store in items table (including quantities)
    logger.info("Fetching all items...")
    items = client.get_all_items(force_refresh=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for item in items:
        c.execute("""
            INSERT OR REPLACE INTO items (item_id, name, status, purchased_qty, sold_qty)
            VALUES (?, ?, ?, ?, ?)
        """, (
            item['item_id'],
            item['name'],
            item.get('status', ''),
            item.get('purchased_quantity', 0),
            item.get('sold_quantity', 0)
        ))
    conn.commit()
    conn.close()
    logger.info(f"Stored {len(items)} items with purchase/sales quantities.")

    # Step 2: Process each document type
    for doc_type, id_field, number_field in DOC_TYPES:
        process_document_type(client, doc_type, id_field, number_field)

    # Step 3: Find items that never appear in any document, including their quantities
    logger.info("Finding items with no documents...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Include purchased_qty and sold_qty for double-checking
    c.execute("""
        SELECT i.item_id, i.name, i.status, i.purchased_qty, i.sold_qty
        FROM items i
        LEFT JOIN document_items di ON i.item_id = di.item_id
        WHERE di.item_id IS NULL
        ORDER BY i.name
    """)
    orphan_items = c.fetchall()  # each row: (item_id, name, status, purchased_qty, sold_qty)
    conn.close()

    logger.info(f"Found {len(orphan_items)} items with no documents.")

    # Separate confirmed orphans (zero quantities) from suspicious ones (non-zero quantities)
    confirmed = [item for item in orphan_items if item[3] == 0 and item[4] == 0]
    suspicious = [item for item in orphan_items if item[3] != 0 or item[4] != 0]

    if suspicious:
        logger.warning(f"Among these, {len(suspicious)} items have non-zero purchase/sales quantities but no document links. This may indicate incomplete document fetching or data inconsistency.")
        for s in suspicious:
            logger.warning(f"  {s[1]} (ID: {s[0]}) - Purchased: {s[3]}, Sold: {s[4]}")

    # Step 4: Export to Excel and JSON
    if orphan_items:
        # Prepare data for export (list of dicts for JSON)
        export_data = []
        for item in orphan_items:
            export_data.append({
                "item_id": item[0],
                "name": item[1],
                "status": item[2],
                "purchased_qty": item[3],
                "sold_qty": item[4],
                "is_suspicious": item[3] != 0 or item[4] != 0
            })

        # Generate JSON file (always)
        json_output = args.output.replace('.xlsx', '.json').replace('.csv', '.json')
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Exported JSON to {json_output}")

        # Try to export Excel, fallback to CSV
        try:
            import pandas as pd
            df = pd.DataFrame(export_data)
            # Reorder columns for readability
            df = df[["item_id", "name", "status", "purchased_qty", "sold_qty", "is_suspicious"]]
            df.to_excel(args.output, index=False)
            logger.info(f"Exported Excel to {args.output}")
        except ImportError:
            logger.error("pandas not installed. Exporting to CSV instead.")
            csv_output = args.output.replace('.xlsx', '.csv')
            with open(csv_output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["item_id", "name", "status", "purchased_qty", "sold_qty", "is_suspicious"])
                writer.writeheader()
                writer.writerows(export_data)
            logger.info(f"Exported CSV to {csv_output}")
    else:
        logger.info("No items without documents found.")

if __name__ == "__main__":
    main()