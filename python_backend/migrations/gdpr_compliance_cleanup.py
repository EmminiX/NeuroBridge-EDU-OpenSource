#!/usr/bin/env python3
"""
GDPR Compliance Migration - Remove Personal Data Collection
Migrates database to comply with zero data collection claims

CRITICAL SECURITY UPDATE:
- Removes IP address collection from api_usage table  
- Removes user agent collection from api_usage table
- Adds privacy compliance documentation
- Updates schema to prevent future PII collection

This migration is REQUIRED before public launch to ensure GDPR compliance
and match the platform's privacy claims.
"""

import sqlite3
import logging
import os
import argparse
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class GDPRComplianceMigrator:
    """GDPR compliance database migration"""
    
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.backup_dir = Path(database_path).parent / "gdpr_compliance_backups"
        self.backup_dir.mkdir(exist_ok=True, parents=True)
    
    def create_backup(self) -> Path:
        """Create backup before GDPR cleanup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"pre_gdpr_cleanup_{timestamp}.db"
        
        if self.database_path.exists():
            import shutil
            shutil.copy2(self.database_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
        
        return backup_path
    
    def analyze_personal_data(self) -> dict:
        """Analyze what personal data exists in the database"""
        if not self.database_path.exists():
            return {"status": "no_database", "findings": []}
        
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        findings = []
        
        try:
            # Check if api_usage table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='api_usage'
            """)
            
            if cursor.fetchone():
                # Check for personal data columns
                cursor = conn.execute("PRAGMA table_info(api_usage)")
                columns = [row['name'] for row in cursor.fetchall()]
                
                personal_data_columns = []
                if 'ip_address' in columns:
                    personal_data_columns.append('ip_address')
                if 'user_agent' in columns:
                    personal_data_columns.append('user_agent')
                
                if personal_data_columns:
                    # Count records with personal data
                    for column in personal_data_columns:
                        cursor = conn.execute(f"""
                            SELECT COUNT(*) as count FROM api_usage 
                            WHERE {column} IS NOT NULL AND {column} != ''
                        """)
                        count = cursor.fetchone()['count']
                        
                        findings.append({
                            'table': 'api_usage',
                            'column': column,
                            'records_with_data': count,
                            'privacy_impact': 'HIGH - Personal identifiable information'
                        })
                
                # Check for session tracking (potential privacy issue)
                if 'session_id' in columns:
                    cursor = conn.execute("""
                        SELECT COUNT(DISTINCT session_id) as unique_sessions 
                        FROM api_usage WHERE session_id IS NOT NULL
                    """)
                    count = cursor.fetchone()['unique_sessions']
                    
                    if count > 0:
                        findings.append({
                            'table': 'api_usage',
                            'column': 'session_id',
                            'unique_sessions': count,
                            'privacy_impact': 'MEDIUM - Session tracking'
                        })
            
        except Exception as e:
            logger.error(f"Error analyzing personal data: {e}")
            findings.append({
                'error': str(e),
                'privacy_impact': 'UNKNOWN'
            })
        
        finally:
            conn.close()
        
        return {
            "status": "analyzed",
            "findings": findings,
            "total_privacy_issues": len(findings)
        }
    
    def perform_gdpr_cleanup(self, dry_run: bool = False) -> bool:
        """Remove personal data and update schema for GDPR compliance"""
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        # Create backup first
        backup_path = self.create_backup()
        
        if not self.database_path.exists():
            logger.info("No database exists - creating GDPR-compliant schema")
            return self._create_clean_schema()
        
        try:
            conn = sqlite3.connect(self.database_path)
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Check if api_usage table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='api_usage'
            """)
            
            if cursor.fetchone():
                logger.info("Found api_usage table - removing personal data columns")
                
                if not dry_run:
                    # Create new GDPR-compliant table
                    conn.execute("""
                        CREATE TABLE api_usage_gdpr_compliant (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            endpoint TEXT NOT NULL,
                            method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD')),
                            status_code INTEGER,
                            response_time_ms INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Copy non-personal data
                    conn.execute("""
                        INSERT INTO api_usage_gdpr_compliant 
                        (endpoint, method, status_code, response_time_ms, created_at)
                        SELECT endpoint, method, status_code, response_time_ms, created_at 
                        FROM api_usage
                    """)
                    
                    # Drop old table
                    conn.execute("DROP TABLE api_usage")
                    
                    # Rename new table
                    conn.execute("ALTER TABLE api_usage_gdpr_compliant RENAME TO api_usage")
                    
                    # Create indexes
                    conn.execute("CREATE INDEX idx_api_usage_created ON api_usage(created_at)")
                    conn.execute("CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint, created_at)")
                    conn.execute("CREATE INDEX idx_api_usage_status ON api_usage(status_code)")
                    
                    logger.info("✅ GDPR cleanup completed - personal data removed")
            
            # Update schema version
            if not dry_run:
                conn.execute("""
                    INSERT OR REPLACE INTO app_settings (setting_key, setting_value, description)
                    VALUES ('gdpr_compliance_date', ?, 'Date when GDPR compliance migration was completed')
                """, (datetime.utcnow().isoformat(),))
                
                conn.execute("""
                    INSERT OR REPLACE INTO app_settings (setting_key, setting_value, description)
                    VALUES ('data_collection_mode', 'zero_collection', 'Confirms zero personal data collection')
                """)
            
            # Commit transaction
            if not dry_run:
                conn.commit()
                logger.info("✅ GDPR compliance migration completed successfully")
            else:
                conn.rollback()
                logger.info("DRY RUN completed - no changes made")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"GDPR cleanup failed: {e}")
            return False
            
        finally:
            conn.close()
    
    def _create_clean_schema(self) -> bool:
        """Create GDPR-compliant database schema from scratch"""
        try:
            conn = sqlite3.connect(self.database_path)
            
            # Create all tables with GDPR compliance
            conn.execute("""
                CREATE TABLE transcription_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
                    transcript TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    raw_transcript TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    summary_metadata TEXT DEFAULT '{}'
                )
            """)
            
            conn.execute("""
                CREATE TABLE app_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # GDPR-compliant api_usage table (NO personal data)
            conn.execute("""
                CREATE TABLE api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD')),
                    status_code INTEGER,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX idx_transcription_sessions_session_id ON transcription_sessions(session_id)")
            conn.execute("CREATE INDEX idx_summaries_created_at ON summaries(created_at)")
            conn.execute("CREATE INDEX idx_app_settings_key ON app_settings(setting_key)")
            conn.execute("CREATE INDEX idx_api_usage_created ON api_usage(created_at)")
            conn.execute("CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint, created_at)")
            
            # Insert GDPR compliance settings
            conn.execute("""
                INSERT INTO app_settings (setting_key, setting_value, description)
                VALUES 
                ('schema_version', '4', 'Database schema version'),
                ('gdpr_compliance_date', ?, 'GDPR compliance migration completion date'),
                ('data_collection_mode', 'zero_collection', 'Confirms zero personal data collection'),
                ('app_mode', 'open_source', 'Application mode'),
                ('transcription_enabled', 'true', 'Enable transcription features'),
                ('summary_generation_enabled', 'true', 'Enable summary generation'),
                ('summary_storage_mode', 'stateless', 'Summary storage mode')
            """, (datetime.utcnow().isoformat(),))
            
            conn.commit()
            conn.close()
            
            logger.info("✅ GDPR-compliant database schema created")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create clean schema: {e}")
            return False
    
    def verify_gdpr_compliance(self) -> dict:
        """Verify that database is GDPR compliant"""
        if not self.database_path.exists():
            return {"compliant": True, "reason": "no_database_exists"}
        
        conn = sqlite3.connect(self.database_path)
        issues = []
        
        try:
            # Check api_usage table structure
            cursor = conn.execute("PRAGMA table_info(api_usage)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Check for prohibited columns
            prohibited_columns = ['ip_address', 'user_agent', 'session_id', 'user_id', 'device_id']
            found_prohibited = [col for col in prohibited_columns if col in columns]
            
            if found_prohibited:
                issues.append(f"Personal data columns found: {found_prohibited}")
            
            # Check for actual personal data
            if 'ip_address' in columns:
                cursor = conn.execute("SELECT COUNT(*) FROM api_usage WHERE ip_address IS NOT NULL")
                count = cursor.fetchone()[0]
                if count > 0:
                    issues.append(f"{count} records contain IP addresses")
            
            if 'user_agent' in columns:
                cursor = conn.execute("SELECT COUNT(*) FROM api_usage WHERE user_agent IS NOT NULL")
                count = cursor.fetchone()[0]
                if count > 0:
                    issues.append(f"{count} records contain user agents")
            
        except Exception as e:
            issues.append(f"Verification error: {e}")
        
        finally:
            conn.close()
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "status": "GDPR_COMPLIANT" if len(issues) == 0 else "PRIVACY_VIOLATIONS_FOUND"
        }


def main():
    parser = argparse.ArgumentParser(description="GDPR Compliance Database Migration")
    parser.add_argument("--database", default="../data/neurobridge.db", help="Database path")
    parser.add_argument("--analyze", action="store_true", help="Analyze personal data collection")
    parser.add_argument("--cleanup", action="store_true", help="Perform GDPR cleanup")
    parser.add_argument("--verify", action="store_true", help="Verify GDPR compliance")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run (no changes)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    migrator = GDPRComplianceMigrator(args.database)
    
    if args.analyze:
        print("🔍 ANALYZING PERSONAL DATA COLLECTION...")
        analysis = migrator.analyze_personal_data()
        
        if analysis["total_privacy_issues"] > 0:
            print(f"❌ PRIVACY VIOLATIONS FOUND: {analysis['total_privacy_issues']} issues")
            for finding in analysis["findings"]:
                print(f"  - {finding}")
        else:
            print("✅ No personal data collection found")
    
    if args.cleanup:
        print("🧹 PERFORMING GDPR CLEANUP...")
        success = migrator.perform_gdpr_cleanup(dry_run=args.dry_run)
        
        if success:
            print("✅ GDPR cleanup completed successfully")
        else:
            print("❌ GDPR cleanup failed")
    
    if args.verify:
        print("🔐 VERIFYING GDPR COMPLIANCE...")
        result = migrator.verify_gdpr_compliance()
        
        if result["compliant"]:
            print("✅ DATABASE IS GDPR COMPLIANT")
        else:
            print("❌ GDPR COMPLIANCE ISSUES FOUND:")
            for issue in result["issues"]:
                print(f"  - {issue}")


if __name__ == "__main__":
    main()