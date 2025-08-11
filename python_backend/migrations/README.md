# Database Migration: Clean Student Schema

This directory contains migration scripts to clean up the NeuroBridge EDU database for the open source version by removing student management functionality.

## Overview

The open source version of NeuroBridge EDU focuses on core transcription and summarization features. This migration removes:
- `students` table (student contact information)
- `send_logs` table (webhook delivery tracking)
- Associated indexes and constraints

## Files

- `clean_student_schema.py` - Main migration script
- `test_migration.py` - Comprehensive migration testing
- `README.md` - This documentation

## Migration Process

### Automatic Migration

The application will automatically detect and run the migration when starting up if:
- Database version is less than 4
- Student or send_log tables exist in the database

### Manual Migration

For more control, run the migration manually:

```bash
# Navigate to python_backend directory
cd python_backend

# Test migration (safe, no changes)
python migrations/clean_student_schema.py --dry-run

# Run actual migration
python migrations/clean_student_schema.py

# Run with custom backup directory
python migrations/clean_student_schema.py --backup-dir /path/to/backups
```

## Safety Features

### Automatic Backup
- Creates timestamped backup before any changes
- Backup includes full database state
- Backup path is logged for recovery

### Transactional Execution
- All changes wrapped in SQLite transaction
- Either all changes succeed or none are applied
- Automatic rollback on failure

### Foreign Key Integrity
- Enables foreign key constraints during migration
- Validates integrity after changes
- Prevents orphaned data

### Version Tracking
- Uses `PRAGMA user_version` for migration state
- Prevents duplicate migrations
- Supports incremental schema updates

## Migration Details

### Current Database State
- Database version: 0 (or unset)
- Tables: students (9 rows), send_logs (19 rows)
- Foreign keys: send_logs → students, send_logs → summaries

### Post-Migration State
- Database version: 4
- Removed tables: students, send_logs
- Preserved tables: summaries, app_settings, api_usage, transcription_sessions
- All data integrity maintained

### Data Impact
- **LOST**: Student contact information and webhook delivery logs
- **PRESERVED**: All transcription sessions, summaries, app settings, usage data

## Testing

### Comprehensive Test Suite
```bash
# Test with current database
python migrations/test_migration.py --db-path ../data/neurobridge.db

# Test with mock data
python migrations/test_migration.py
```

### Test Coverage
- Pre-migration state validation
- Migration execution verification
- Post-migration data integrity
- Foreign key constraint validation
- Schema version verification

## Recovery

### Rollback from Backup
If migration issues occur, restore from backup:

```bash
# Find backup file (logged during migration)
ls backups/

# Restore from backup
cp backups/neurobridge_backup_YYYYMMDD_HHMMSS_pre_migration_v4.db ../data/neurobridge.db
```

### Manual Recovery
```python
# Using migration script
python migrations/clean_student_schema.py --rollback /path/to/backup.db
```

## New Installations

New installations automatically get the clean schema without student management:
- Only core tables created
- No migration needed
- Clean, optimized structure

## Schema Version History

- **v0**: Original schema with student management
- **v1-3**: Reserved for future use
- **v4**: Clean schema without student management (target)

## Verification

After migration, verify the clean state:

```sql
-- Check schema version
PRAGMA user_version;  -- Should be 4

-- Verify tables removed
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('students', 'send_logs');
-- Should return no rows

-- Check foreign key integrity
PRAGMA foreign_key_check;
-- Should return no violations

-- Verify data preservation
SELECT COUNT(*) FROM summaries;
SELECT COUNT(*) FROM transcription_sessions;
SELECT COUNT(*) FROM app_settings;
```

## Troubleshooting

### Common Issues

**Migration fails with foreign key error**
- Check for referential integrity issues
- Review backup and restore if needed

**Database locked error**
- Ensure no other processes using database
- Stop application before manual migration

**Version mismatch after migration**
- Check PRAGMA user_version output
- May need to manually set version

### Support

For issues with migration:
1. Check logs for detailed error messages
2. Verify backup files are available
3. Review foreign key integrity
4. Test migration on database copy first

## Implementation Notes

### SQLite Specific Features
- Uses WAL journal mode for safety
- Enables foreign key constraints
- Leverages PRAGMA user_version for versioning

### Python Dependencies
- No external dependencies beyond stdlib
- Compatible with Python 3.8+
- Uses SQLite native bindings

### Performance
- Fast migration (completes in seconds)
- Minimal downtime required
- Efficient backup process

This migration ensures a clean, maintainable database structure focused on core NeuroBridge EDU functionality while preserving all important data.