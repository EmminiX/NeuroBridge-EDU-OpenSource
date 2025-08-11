#!/usr/bin/env python3
"""
Database Schema Verification Script

Verifies that the database has been successfully migrated to the clean
schema without student management functionality.

Usage:
    python verify_clean_schema.py [--db-path=/path/to/database.db]
"""

import sqlite3
import argparse
import sys
from pathlib import Path

def verify_clean_schema(db_path: str) -> bool:
    """
    Verify the database is in the expected clean state
    
    Returns:
        bool: True if schema is clean and valid
    """
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        
        print(f"🔍 Verifying database schema: {db_path}")
        print("=" * 60)
        
        # Check schema version
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 4:
            print(f"✅ Schema version: {version} (correct)")
        else:
            print(f"❌ Schema version: {version} (expected 4)")
            return False
        
        # Check tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        
        print(f"📋 Tables found: {len(table_names)}")
        for table in sorted(table_names):
            if table != 'sqlite_sequence':
                print(f"   • {table}")
        
        # Verify student tables are removed
        student_tables = ['students', 'send_logs']
        removed_correctly = True
        for table in student_tables:
            if table in table_names:
                print(f"❌ Student table still exists: {table}")
                removed_correctly = False
            else:
                print(f"✅ Student table removed: {table}")
        
        if not removed_correctly:
            return False
        
        # Verify core tables exist
        expected_tables = ['summaries', 'transcription_sessions', 'app_settings', 'api_usage']
        core_tables_ok = True
        for table in expected_tables:
            if table in table_names:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"✅ Core table exists: {table} ({count} rows)")
            else:
                print(f"❌ Core table missing: {table}")
                core_tables_ok = False
        
        if not core_tables_ok:
            return False
        
        # Check foreign key integrity
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            print(f"❌ Foreign key violations found: {len(violations)}")
            for violation in violations[:5]:  # Show first 5
                print(f"   • {violation}")
            return False
        else:
            print("✅ Foreign key integrity: No violations")
        
        # Check indexes
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'").fetchall()
        index_names = [i[0] for i in indexes]
        print(f"🔗 Indexes found: {len(index_names)}")
        
        # Verify no student-related indexes remain
        student_indexes = [idx for idx in index_names if 'student' in idx.lower() or 'send_log' in idx.lower()]
        if student_indexes:
            print(f"❌ Student-related indexes still exist: {student_indexes}")
            return False
        else:
            print("✅ Student-related indexes removed")
        
        conn.close()
        
        print("=" * 60)
        print("🎉 Database schema verification PASSED!")
        print("   Database is ready for open source deployment.")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Verify clean database schema")
    parser.add_argument("--db-path", default="../data/neurobridge.db", 
                       help="Path to database file")
    
    args = parser.parse_args()
    
    # Resolve database path
    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = (Path(__file__).parent / args.db_path).resolve()
    
    success = verify_clean_schema(str(db_path))
    
    if success:
        print("\n✨ Schema verification completed successfully!")
        return 0
    else:
        print("\n💥 Schema verification failed!")
        print("   Please review migration or run cleanup again.")
        return 1

if __name__ == "__main__":
    exit(main())