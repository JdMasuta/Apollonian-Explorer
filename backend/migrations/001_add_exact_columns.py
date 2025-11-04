"""
Database migration: Add exact arithmetic TEXT columns to circles table.

Reference: .DESIGN_SPEC.md Section 8.4 - Hybrid Exact Arithmetic System

This migration adds TEXT columns for storing exact arithmetic values in tagged format:
- curvature_exact: TEXT (format: "int:6", "frac:3/2", "sym:sqrt(2)")
- center_x_exact: TEXT
- center_y_exact: TEXT
- radius_exact: TEXT

The existing INTEGER columns (curvature_num/denom, etc.) are preserved for:
1. Backward compatibility with existing queries
2. Fast numeric comparisons and indexing
3. Fallback if exact values are not set

Migration Strategy:
- ADD COLUMN operations are idempotent (SQLite ignores if column exists)
- No data migration initially (new columns nullable)
- Future inserts will populate both INTEGER and TEXT columns
- Existing rows remain valid with NULL exact columns

Usage:
    from migrations.001_add_exact_columns import migrate_up, migrate_down

    # Apply migration
    migrate_up(engine)

    # Rollback migration (optional, for testing)
    migrate_down(engine)
"""

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
import logging

logger = logging.getLogger(__name__)


def migrate_up(engine: Engine) -> None:
    """
    Apply migration: Add exact arithmetic TEXT columns.

    Args:
        engine: SQLAlchemy engine connected to database

    Raises:
        OperationalError: If migration fails (other than column already exists)
    """
    logger.info("Starting migration 001: Add exact arithmetic columns")

    columns_to_add = [
        ("curvature_exact", "TEXT"),
        ("center_x_exact", "TEXT"),
        ("center_y_exact", "TEXT"),
        ("radius_exact", "TEXT"),
    ]

    with engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            try:
                # SQLite: ALTER TABLE ADD COLUMN is idempotent (safe if exists)
                sql = text(f"ALTER TABLE circles ADD COLUMN {column_name} {column_type}")
                conn.execute(sql)
                conn.commit()
                logger.info(f"✓ Added column: circles.{column_name}")
            except OperationalError as e:
                # Check if error is "duplicate column name" (expected if already migrated)
                if "duplicate column name" in str(e).lower():
                    logger.info(f"⊘ Column already exists: circles.{column_name} (skipping)")
                else:
                    logger.error(f"✗ Failed to add column: circles.{column_name}")
                    raise

    logger.info("✓ Migration 001 complete: All exact columns added")


def migrate_down(engine: Engine) -> None:
    """
    Rollback migration: Remove exact arithmetic TEXT columns.

    WARNING: This will delete exact arithmetic data. Only use for testing/rollback.

    Args:
        engine: SQLAlchemy engine connected to database
    """
    logger.warning("Rolling back migration 001: Removing exact arithmetic columns")

    columns_to_remove = [
        "curvature_exact",
        "center_x_exact",
        "center_y_exact",
        "radius_exact",
    ]

    with engine.connect() as conn:
        # SQLite doesn't support DROP COLUMN directly (until SQLite 3.35+)
        # Need to check SQLite version and use appropriate method

        # Check if we can drop columns directly
        try:
            for column_name in columns_to_remove:
                sql = text(f"ALTER TABLE circles DROP COLUMN {column_name}")
                conn.execute(sql)
                conn.commit()
                logger.info(f"✓ Removed column: circles.{column_name}")
        except OperationalError as e:
            if "no such column" in str(e).lower():
                logger.info(f"⊘ Column doesn't exist: {column_name} (skipping)")
            elif "drop column" in str(e).lower():
                logger.warning(
                    "SQLite version doesn't support DROP COLUMN. "
                    "Migration rollback requires manual table rebuild or newer SQLite."
                )
                logger.warning(
                    "Columns will remain in table but can be ignored. "
                    "Future code will not use them."
                )
            else:
                logger.error(f"✗ Failed to remove column: {column_name}")
                raise

    logger.info("Migration 001 rollback complete")


def migrate_existing_data(engine: Engine) -> None:
    """
    Optional: Migrate existing INTEGER data to TEXT exact format.

    This function converts existing circles from INTEGER num/denom format
    to TEXT exact format (as Fractions). This is optional because:
    - New code will populate both formats
    - Old INTEGER data remains valid
    - Exact columns being NULL just means "use INTEGER fallback"

    Only run this if you want to populate exact columns for existing data.

    Args:
        engine: SQLAlchemy engine connected to database
    """
    logger.info("Migrating existing circle data to exact format")

    from fractions import Fraction
    from core.exact_math import format_exact

    with engine.connect() as conn:
        # Get all circles with NULL exact columns
        result = conn.execute(text("""
            SELECT id,
                   curvature_num, curvature_denom,
                   center_x_num, center_x_denom,
                   center_y_num, center_y_denom,
                   radius_num, radius_denom
            FROM circles
            WHERE curvature_exact IS NULL
        """))

        circles = result.fetchall()
        logger.info(f"Found {len(circles)} circles to migrate")

        for circle in circles:
            circle_id = circle[0]

            # Convert INTEGER pairs to Fraction, then to exact format
            curvature = Fraction(circle[1], circle[2])
            center_x = Fraction(circle[3], circle[4])
            center_y = Fraction(circle[5], circle[6])
            radius = Fraction(circle[7], circle[8])

            # Format as tagged strings
            curvature_exact = format_exact(curvature)
            center_x_exact = format_exact(center_x)
            center_y_exact = format_exact(center_y)
            radius_exact = format_exact(radius)

            # Update circle with exact values
            conn.execute(text("""
                UPDATE circles
                SET curvature_exact = :curvature,
                    center_x_exact = :center_x,
                    center_y_exact = :center_y,
                    radius_exact = :radius
                WHERE id = :id
            """), {
                "id": circle_id,
                "curvature": curvature_exact,
                "center_x": center_x_exact,
                "center_y": center_y_exact,
                "radius": radius_exact,
            })

        conn.commit()
        logger.info(f"✓ Migrated {len(circles)} circles to exact format")


def verify_migration(engine: Engine) -> bool:
    """
    Verify that migration was applied successfully.

    Args:
        engine: SQLAlchemy engine connected to database

    Returns:
        True if all exact columns exist, False otherwise
    """
    with engine.connect() as conn:
        # Query table schema
        result = conn.execute(text("PRAGMA table_info(circles)"))
        columns = {row[1] for row in result.fetchall()}  # row[1] is column name

        required_columns = {
            "curvature_exact",
            "center_x_exact",
            "center_y_exact",
            "radius_exact",
        }

        missing = required_columns - columns

        if missing:
            logger.error(f"Migration incomplete. Missing columns: {missing}")
            return False
        else:
            logger.info("✓ Migration verified: All exact columns present")
            return True


# Convenience function for easy import
def apply_migration(engine: Engine, migrate_data: bool = False) -> None:
    """
    Apply migration with optional data migration.

    Args:
        engine: SQLAlchemy engine
        migrate_data: If True, also migrate existing INTEGER data to exact format
    """
    migrate_up(engine)

    if verify_migration(engine):
        if migrate_data:
            migrate_existing_data(engine)
        logger.info("✓ Migration 001 applied successfully")
    else:
        raise RuntimeError("Migration verification failed")


if __name__ == "__main__":
    """
    Run migration directly from command line.

    Usage:
        python migrations/001_add_exact_columns.py
    """
    import sys
    from pathlib import Path

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from db.base import engine

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Apply migration
    apply_migration(engine, migrate_data=False)

    print("\n" + "="*60)
    print("Migration 001 applied successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update Circle model to use exact columns (Phase 4)")
    print("2. Update gasket generation to populate exact columns (Phase 5-6)")
    print("3. Optionally run migrate_existing_data() to convert old data")
