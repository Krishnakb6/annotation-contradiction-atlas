"""
Schema inspection and validation utilities for The Annotation Contradiction Atlas.
"""
from __future__ import annotations

from typing import Dict, Any, List
from sqlalchemy import inspect
from database.connection import engine
from database.models import Base


def get_schema_summary() -> Dict[str, Any]:
    """
    Inspect the active database tables, columns, and foreign keys.
    """
    inspector = inspect(engine)
    summary = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        indexes = inspector.get_indexes(table_name)
        summary[table_name] = {
            "columns": [{"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]} for c in columns],
            "foreign_keys": [
                {"constrained_columns": fk["constrained_columns"], "referred_table": fk["referred_table"], "referred_columns": fk["referred_columns"]}
                for fk in foreign_keys
            ],
            "indexes": [{"name": idx["name"], "columns": idx["column_names"], "unique": idx["unique"]} for idx in indexes],
        }
    return summary


def verify_schema_integrity() -> Dict[str, bool]:
    """
    Verify that all expected ORM models exist in the database.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = {table.name for table in Base.metadata.sorted_tables}

    return {
        table: (table in existing_tables)
        for table in expected_tables
    }
