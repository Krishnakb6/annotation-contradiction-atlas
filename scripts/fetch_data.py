"""
Command-line data acquisition script for The Annotation Contradiction Atlas.
Fetches human protein kinase records from UniProtKB REST API and stores them in the database.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import init_db
from services.data_import import DataImportService
from config import DEFAULT_MAX_RECORDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("atlas.fetch_data")


def main():
    parser = argparse.ArgumentParser(description="Fetch human protein kinase records from UniProt")
    parser.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS, help="Maximum records to retrieve")
    parser.add_argument("--include-unreviewed", action="store_true", help="Include unreviewed (TrEMBL) records")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass local cache and query live UniProt API")
    parser.add_argument("--init-db", action="store_true", help="Initialize or recreate database tables")
    args = parser.parse_args()

    if args.init_db:
        logger.info("Initializing database schema...")
        init_db(drop_all=False)

    service = DataImportService()
    logger.info(f"Starting import: max_records={args.max_records}, reviewed_only={not args.include_unreviewed}")

    summary = service.import_kinases(
        max_records=args.max_records,
        reviewed_only=not args.include_unreviewed,
        force_refresh=args.force_refresh,
        use_fallback_if_failed=True,
    )

    print("\n" + "="*50)
    print("UNIPROT DATA INGESTION SUMMARY")
    print("="*50)
    print(f"Source:           {summary['source']}")
    print(f"Total Processed:  {summary['total_processed']}")
    print(f"Newly Inserted:   {summary['newly_inserted']}")
    print(f"Updated Records:  {summary['updated']}")
    print(f"Annotations:      {summary['annotations_saved']}")
    print(f"Timestamp:        {summary['timestamp']}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
