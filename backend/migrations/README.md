# Database Migrations

This directory contains database schema migrations for the Apollonian Gasket project.

## Migration System

We use a simple Python-based migration system (not Alembic) for maximum control and transparency. Each migration is a standalone Python script that can be run independently.

## Available Migrations

### 001_add_exact_columns.py

**Purpose**: Add TEXT columns for hybrid exact arithmetic storage

**Changes**:
- Adds `curvature_exact` (TEXT) column
- Adds `center_x_exact` (TEXT) column
- Adds `center_y_exact` (TEXT) column
- Adds `radius_exact` (TEXT) column

**Preserves**:
- All existing INTEGER columns (curvature_num/denom, etc.)
- All existing data
- All existing indexes

**Status**: Required for hybrid exact arithmetic (Phase 3)

## Running Migrations

### Method 1: From Python code

```python
from db.base import engine
from migrations import apply_migration

# Apply migration (creates columns)
apply_migration(engine)

# Apply migration + migrate existing data
apply_migration(engine, migrate_data=True)
```

### Method 2: Command line

```bash
cd backend
. venv/bin/activate
python migrations/001_add_exact_columns.py
```

### Method 3: From main.py startup

Add to `main.py`:

```python
from migrations import apply_migration
from db.base import engine

@app.on_event("startup")
async def startup():
    # Apply pending migrations
    apply_migration(engine)
```

## Migration Verification

To verify a migration was applied:

```python
from db.base import engine
from migrations.001_add_exact_columns import verify_migration

if verify_migration(engine):
    print("Migration 001 applied successfully")
else:
    print("Migration 001 not applied")
```

## Rollback (Testing Only)

**WARNING**: Rollback will delete exact arithmetic data. Only use in development.

```python
from db.base import engine
from migrations.001_add_exact_columns import migrate_down

migrate_down(engine)
```

Note: SQLite versions before 3.35 don't support DROP COLUMN. In that case, columns remain but are unused.

## Migration Safety

All migrations are designed to be:
- **Idempotent**: Safe to run multiple times
- **Non-destructive**: Preserve existing data
- **Backward compatible**: Old code still works after migration

## Creating New Migrations

1. Create new file: `migrations/00N_description.py`
2. Implement functions:
   - `migrate_up(engine)` - Apply migration
   - `migrate_down(engine)` - Rollback (optional)
   - `verify_migration(engine)` - Verify success
3. Add imports to `migrations/__init__.py`
4. Document in this README
5. Test thoroughly before applying to production

## Migration Order

Migrations must be applied in order:
1. 001_add_exact_columns (Phase 3)
2. Future migrations...

## Troubleshooting

### "duplicate column name" error

This is expected if migration was already applied. The migration script handles this gracefully.

### SQLite version doesn't support DROP COLUMN

Upgrade SQLite to 3.35+, or accept that rollback leaves unused columns in table.

### Import errors

Make sure to run from backend/ directory:
```bash
cd backend
python migrations/001_add_exact_columns.py
```

## Related Documentation

- `.DESIGN_SPEC.md` Section 8.4 - Hybrid Exact Arithmetic System
- `.DESIGN_SPEC.md` Section 4.2 - Database Schema
- `core/exact_math.py` - Exact arithmetic implementation
