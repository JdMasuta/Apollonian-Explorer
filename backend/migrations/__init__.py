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

Note: migration module names start with digits, so they cannot be imported
with a plain ``import`` statement. Run them as scripts::

    python migrations/001_add_exact_columns.py

or load them programmatically with ``importlib.import_module("migrations")``
plus ``importlib.util.spec_from_file_location`` for the numbered module.
(The previous ``from migrations.001_... import ...`` here was a syntax error
that broke any import of this package.)
"""
