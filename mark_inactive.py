#!/usr/bin/env python3
"""
Script to mark items as inactive based on the JSON output from extagnant.py.
Reads a JSON file containing items with no documents and updates their status
to 'inactive' in Zoho Books.

Respects API rate limits and logs all actions.
"""

import json
import time
import logging
import argparse
from pathlib import Path
from zoho_api import ZohoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rate limiting: 0.6 seconds between requests = 100 per minute
REQUEST_DELAY = 0.6

def main():
    parser = argparse.ArgumentParser(
        description="Mark items from a JSON file as inactive in Zoho Books."
    )
    parser.add_argument(
        "--input", "-i",
        default="items_sin_documentos.json",
        help="Input JSON file (default: items_sin_documentos.json)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Perform a dry run without making any API calls"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip items that are already inactive (check via API or rely on JSON status)"
    )
    args = parser.parse_args()

    # Check if input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    # Load JSON data
    with open(input_path, 'r', encoding='utf-8') as f:
        items = json.load(f)

    logger.info(f"Loaded {len(items)} items from {input_path}")

    # Optional: filter by status from JSON (if present)
    if args.skip_existing:
        # The JSON includes 'status' field from the original extagnant output
        # Only process items that are currently 'active'
        items_to_process = [item for item in items if item.get('status') == 'active']
        skipped_count = len(items) - len(items_to_process)
        logger.info(f"Skipping {skipped_count} items already marked as inactive in JSON.")
    else:
        items_to_process = items

    if not items_to_process:
        logger.info("No active items to process.")
        return

    if args.dry_run:
        logger.info("DRY RUN: Would mark the following items as inactive:")
        for item in items_to_process:
            logger.info(f"  - {item.get('name')} (ID: {item.get('item_id')})")
        logger.info(f"Total items to mark: {len(items_to_process)}")
        return

    # Initialize Zoho client
    try:
        client = ZohoClient()
    except Exception as e:
        logger.error(f"Failed to initialize ZohoClient: {e}")
        return

    # Process each item
    success_count = 0
    fail_count = 0
    already_inactive_count = 0

    for idx, item in enumerate(items_to_process, 1):
        item_id = item.get('item_id')
        item_name = item.get('name', 'Unknown')
        if not item_id:
            logger.warning(f"Skipping item without item_id: {item}")
            continue

        # Optional: skip if already inactive (if we didn't filter by JSON)
        if not args.skip_existing and item.get('status') == 'inactive':
            logger.info(f"Item {item_name} (ID: {item_id}) already inactive (from JSON). Skipping.")
            already_inactive_count += 1
            continue

        # Call API to mark inactive
        try:
            logger.info(f"[{idx}/{len(items_to_process)}] Marking '{item_name}' (ID: {item_id}) as inactive...")
            if not args.dry_run:
                # update_item_status(activate=False) means deactivate
                client.update_item_status(item_id, activate=False)
                # Optional: verify after update? Could fetch details but that would add another API call.
                logger.info(f"Successfully marked '{item_name}' as inactive.")
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to mark '{item_name}' (ID: {item_id}): {e}")
            fail_count += 1

        # Rate limiting delay
        time.sleep(REQUEST_DELAY)

    # Summary
    logger.info("=" * 50)
    logger.info("Processing complete.")
    if args.skip_existing:
        logger.info(f"Skipped (already inactive per JSON): {skipped_count}")
    else:
        logger.info(f"Already inactive (checked from JSON): {already_inactive_count}")
    logger.info(f"Successfully marked inactive: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()