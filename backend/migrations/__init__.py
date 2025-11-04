"""
Database migrations package.

This package contains database schema migrations for the Apollonian Gasket project.

Each migration is numbered sequentially and includes:
- migrate_up(): Apply the migration
- migrate_down(): Rollback the migration (if possible)
- verify_migration(): Verify migration was applied

Reference: .DESIGN_SPEC.md Section 8.4 - Hybrid Exact Arithmetic System

Available Migrations:
- 001_add_exact_columns: Add TEXT columns for hybrid exact arithmetic
"""

from migrations.001_add_exact_columns import (
    migrate_up,
    migrate_down,
    migrate_existing_data,
    verify_migration,
    apply_migration,
)

__all__ = [
    "migrate_up",
    "migrate_down",
    "migrate_existing_data",
    "verify_migration",
    "apply_migration",
]
