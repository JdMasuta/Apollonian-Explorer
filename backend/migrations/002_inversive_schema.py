"""
Migration 002: schema v2 — inversive coordinates.

Reference: REVAMP_BLUEPRINT.md Milestone 2.

Replaces the v1 circles layout (dual INTEGER num/denom pairs + tagged TEXT
columns + JSON parent/tangent ids) with the engine-native representation:
group word (UNIQUE per gasket), exact inversive coordinate strings, and
indexed float mirrors. Adds gaskets.min_radius_cached.

DESTRUCTIVE: the circles and gaskets tables are dropped and recreated.
All stored data is regenerable cache (no user data), so this migration
recreates empty tables; gaskets repopulate on first request.

Run as a script:
    python migrations/002_inversive_schema.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from db.base import Base, engine  # noqa: E402


def migrate_up() -> None:
    """Drop v1 tables and recreate the v2 schema."""
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS circles"))
        conn.execute(text("DROP TABLE IF EXISTS gaskets"))
    Base.metadata.create_all(bind=engine)
    print("✓ schema v2 created (circles regenerate on demand)")


def migrate_down() -> None:
    """Rollback is not supported: v1 data is not preserved.

    Check out a pre-v2 revision and run create_tables() to restore the old
    layout (also empty — the data was cache).
    """
    raise NotImplementedError("002 is destructive; see docstring for manual rollback")


def verify_migration() -> bool:
    """Verify the v2 columns exist."""
    inspector = inspect(engine)
    circle_columns = {c["name"] for c in inspector.get_columns("circles")}
    gasket_columns = {c["name"] for c in inspector.get_columns("gaskets")}
    required = {
        "word",
        "is_line",
        "cocurvature_exact",
        "curvature_exact",
        "kx_exact",
        "ky_exact",
        "b_f",
        "x_f",
        "y_f",
        "r_f",
    }
    ok = required <= circle_columns and "min_radius_cached" in gasket_columns
    print(f"✓ schema v2 verified: {ok}")
    return ok


def apply_migration() -> None:
    migrate_up()
    if not verify_migration():
        raise RuntimeError("Migration verification failed")


if __name__ == "__main__":
    apply_migration()
