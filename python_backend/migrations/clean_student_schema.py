#!/usr/bin/env python3
"""
Database Migration: Clean Student Schema for Open Source Version

This migration removes all student management functionality from the database:
- Removes 'students' table 
- Removes 'send_logs' table
- Cleans up associated indexes
- Maintains data integrity for core functionality

Migration is safe and includes:
- Automatic backup before changes
- Transactional execution (all-or-nothing)
- Foreign key integrity checks
- Version tracking to prevent duplicate execution
- Rollback capabilities

Usage:
    python clean_student_schema.py [--backup-dir=/path/to/backups] [--dry-run]
"""

import sqlite3
import argparse
import logging
import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Migration metadata
MIGRATION_VERSION = 4
MIGRATION_NAME = "clean_student_schema"
DATABASE_PATH = "../data/neurobridge.db"

class MigrationError(Exception):
    """Custom exception for migration-related errors"""
    pass

class DatabaseMigrator:
    """Handles safe database schema migrations with backup and rollback"""
    
    def __init__(self, db_path: str, backup_dir: Optional[str] = None):
        self.db_path = Path(db_path).resolve()
        self.backup_dir = Path(backup_dir) if backup_dir else self.db_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        if not self.db_path.exists():
            raise MigrationError(f"Database file not found: {self.db_path}")
    
    def create_backup(self) -> Path:
        """Create a backup of the database before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"neurobridge_backup_{timestamp}_pre_migration_v{MIGRATION_VERSION}.db"
        backup_path = self.backup_dir / backup_name
        
        logger.info(f"Creating backup: {backup_path}")
        shutil.copy2(self.db_path, backup_path)
        
        # Verify backup integrity
        if not backup_path.exists() or backup_path.stat().st_size == 0:
            raise MigrationError(f"Backup creation failed: {backup_path}")
        
        logger.info(f"Backup created successfully: {backup_path}")
        return backup_path
    
    @contextmanager
    def get_connection(self, enable_fk: bool = True):
        """Get database connection with proper configuration"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency and safety
            if enable_fk:
                conn.execute("PRAGMA foreign_keys=ON")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise MigrationError(f"Database connection error: {e}")
        finally:
            if conn:
                conn.close()
    
    def get_current_version(self) -> int:
        """Get current database schema version"""
        with self.get_connection(enable_fk=False) as conn:
            result = conn.execute("PRAGMA user_version").fetchone()
            return result[0] if result else 0
    
    def set_version(self, version: int) -> None:
        """Set database schema version"""
        with self.get_connection(enable_fk=False) as conn:
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        with self.get_connection(enable_fk=False) as conn:
            result = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ).fetchone()
            return result is not None
    
    def get_table_info(self, table_name: str) -> List[Tuple]:
        """Get table schema information"""
        with self.get_connection(enable_fk=False) as conn:
            return conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    
    def get_foreign_keys(self, table_name: str) -> List[Tuple]:
        """Get foreign key information for a table"""
        with self.get_connection(enable_fk=False) as conn:
            return conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table"""
        if not self.table_exists(table_name):
            return 0
        with self.get_connection(enable_fk=False) as conn:
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
    
    def validate_foreign_key_integrity(self) -> List[Tuple]:
        """Check for foreign key violations"""
        with self.get_connection(enable_fk=True) as conn:
            return conn.execute("PRAGMA foreign_key_check").fetchall()
    
    def analyze_migration_impact(self) -> dict:
        """Analyze what will be affected by the migration"""
        impact = {
            'students_table': {
                'exists': self.table_exists('students'),
                'row_count': self.get_table_row_count('students'),
            },
            'send_logs_table': {
                'exists': self.table_exists('send_logs'),
                'row_count': self.get_table_row_count('send_logs'),
            },
            'current_version': self.get_current_version(),
            'needs_migration': self.get_current_version() < MIGRATION_VERSION
        }
        
        # Check foreign key relationships
        if impact['send_logs_table']['exists']:
            impact['send_logs_table']['foreign_keys'] = self.get_foreign_keys('send_logs')
        
        return impact
    
    def perform_migration(self, dry_run: bool = False) -> bool:
        """Perform the actual migration to remove student-related tables"""
        impact = self.analyze_migration_impact()
        
        logger.info("Migration Impact Analysis:")
        logger.info(f"  Students table: exists={impact['students_table']['exists']}, rows={impact['students_table']['row_count']}")
        logger.info(f"  Send logs table: exists={impact['send_logs_table']['exists']}, rows={impact['send_logs_table']['row_count']}")
        logger.info(f"  Current version: {impact['current_version']}")
        logger.info(f"  Target version: {MIGRATION_VERSION}")
        
        if not impact['needs_migration']:
            logger.info("Database already at target version or higher. No migration needed.")
            return True
        
        if dry_run:
            logger.info("DRY RUN: Would execute the following changes:")
            if impact['send_logs_table']['exists']:
                logger.info("  - DROP TABLE send_logs")
            if impact['students_table']['exists']:
                logger.info("  - DROP TABLE students")
            logger.info(f"  - UPDATE user_version to {MIGRATION_VERSION}")
            return True
        
        # Create backup before making changes
        backup_path = self.create_backup()
        
        try:
            with self.get_connection(enable_fk=True) as conn:
                with conn:  # Transaction context
                    logger.info("Starting database migration...")
                    
                    # Step 1: Remove send_logs table (has foreign keys to students)
                    if impact['send_logs_table']['exists']:
                        logger.info(f"Dropping send_logs table ({impact['send_logs_table']['row_count']} rows)")
                        conn.execute("DROP TABLE send_logs")
                    
                    # Step 2: Remove students table
                    if impact['students_table']['exists']:
                        logger.info(f"Dropping students table ({impact['students_table']['row_count']} rows)")
                        conn.execute("DROP TABLE students")
                    
                    # Step 3: Verify no foreign key violations
                    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
                    if violations:
                        raise MigrationError(f"Foreign key violations detected: {violations}")
                    
                    # Step 4: Update schema version
                    conn.execute(f"PRAGMA user_version = {MIGRATION_VERSION}")
                    
                    logger.info("Migration completed successfully")
                    
            # Final validation
            final_violations = self.validate_foreign_key_integrity()
            if final_violations:
                raise MigrationError(f"Post-migration foreign key violations: {final_violations}")
            
            logger.info(f"Schema successfully migrated to version {MIGRATION_VERSION}")
            logger.info(f"Backup available at: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            logger.info(f"Database backup available at: {backup_path}")
            logger.info("You can restore from backup if needed")
            raise MigrationError(f"Migration failed: {e}")
    
    def rollback_from_backup(self, backup_path: str) -> bool:
        """Rollback database from backup"""
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise MigrationError(f"Backup file not found: {backup_path}")
        
        logger.info(f"Rolling back database from: {backup_path}")
        
        # Create a backup of current state before rollback
        rollback_backup = self.create_backup()
        logger.info(f"Current state backed up to: {rollback_backup}")
        
        # Restore from backup
        shutil.copy2(backup_file, self.db_path)
        
        logger.info("Rollback completed successfully")
        return True

def main():
    """Main migration execution function"""
    parser = argparse.ArgumentParser(description="Clean student schema migration")
    parser.add_argument("--backup-dir", help="Directory for backup files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--rollback", help="Rollback from specified backup file")
    parser.add_argument("--db-path", default=DATABASE_PATH, help="Path to database file")
    
    args = parser.parse_args()
    
    try:
        # Resolve database path
        db_path = Path(args.db_path)
        if not db_path.is_absolute():
            db_path = (Path(__file__).parent / args.db_path).resolve()
        
        migrator = DatabaseMigrator(str(db_path), args.backup_dir)
        
        if args.rollback:
            migrator.rollback_from_backup(args.rollback)
        else:
            migrator.perform_migration(dry_run=args.dry_run)
        
        logger.info("Operation completed successfully")
        
    except MigrationError as e:
        logger.error(f"Migration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())