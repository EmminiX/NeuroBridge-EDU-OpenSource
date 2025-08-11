#!/bin/bash

# NeuroBridgeEDU Database Restore Script
# 
# This script restores the SQLite database from a backup file
# with validation and safety checks.
#
# Usage:
#   ./scripts/restore-db.sh [backup_file] [options]
#
# Options:
#   -f, --force     Skip confirmation prompts
#   -v, --verify    Verify backup integrity before restore
#   -b, --backup    Create backup of current database before restore
#   -h, --help      Show this help message

set -euo pipefail

# Default configuration
DATABASE_PATH="${DATABASE_PATH:-./data/neurobridge.db}"
BACKUP_DIR="./backups"
FORCE=false
VERIFY=true
CREATE_BACKUP=true

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    cat << EOF
NeuroBridgeEDU Database Restore Script

Usage: $0 BACKUP_FILE [OPTIONS]

ARGUMENTS:
    BACKUP_FILE     Path to the backup file to restore

OPTIONS:
    -f, --force     Skip confirmation prompts
    -v, --verify    Verify backup integrity before restore (default: true)
    -b, --backup    Create backup of current database before restore (default: true)
    -h, --help      Show this help message

EXAMPLES:
    $0 backups/neurobridge_20241231_120000_hostname.db
    $0 backups/backup.db -f -v
    $0 /path/to/backup.db --no-backup --force

ENVIRONMENT VARIABLES:
    DATABASE_PATH   Path to current SQLite database (default: $DATABASE_PATH)

EOF
}

# Function to validate backup file
validate_backup_file() {
    local backup_file="$1"
    
    print_status "Validating backup file: $backup_file"
    
    # Check if backup file exists
    if [[ ! -f "$backup_file" ]]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    # Check if backup file is readable
    if [[ ! -r "$backup_file" ]]; then
        print_error "Backup file not readable: $backup_file"
        exit 1
    fi
    
    # Check if backup file appears to be a SQLite database
    if ! file "$backup_file" | grep -q "SQLite"; then
        print_warning "Backup file may not be a valid SQLite database"
        
        if [[ "$FORCE" == false ]]; then
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_status "Restore cancelled"
                exit 0
            fi
        fi
    fi
    
    print_success "Backup file validation passed"
}

# Function to verify backup integrity
verify_backup_integrity() {
    local backup_file="$1"
    
    if [[ "$VERIFY" == false ]]; then
        print_status "Skipping backup integrity verification"
        return
    fi
    
    print_status "Verifying backup integrity..."
    
    # Test if backup database can be opened and queried
    if sqlite3 "$backup_file" "PRAGMA integrity_check;" | grep -q "ok"; then
        print_success "Backup integrity verification passed"
    else
        print_error "Backup integrity verification failed"
        
        if [[ "$FORCE" == false ]]; then
            read -p "Continue with potentially corrupted backup? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_status "Restore cancelled"
                exit 1
            fi
        fi
    fi
    
    # Check basic table structure
    local tables=$(sqlite3 "$backup_file" ".tables" 2>/dev/null || echo "")
    if [[ -n "$tables" ]]; then
        print_status "Found tables in backup: $tables"
    else
        print_warning "No tables found in backup file"
    fi
}

# Function to create backup of current database
create_current_backup() {
    if [[ "$CREATE_BACKUP" == false ]]; then
        print_status "Skipping current database backup"
        return
    fi
    
    if [[ ! -f "$DATABASE_PATH" ]]; then
        print_status "Current database not found, skipping backup"
        return
    fi
    
    print_status "Creating backup of current database..."
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Generate backup filename
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local hostname=$(hostname -s)
    local backup_filename="${BACKUP_DIR}/neurobridge_pre_restore_${timestamp}_${hostname}.db"
    
    # Create backup using SQLite's backup command
    sqlite3 "$DATABASE_PATH" ".backup $backup_filename"
    
    if [[ -f "$backup_filename" ]]; then
        local backup_size
        if command -v numfmt >/dev/null 2>&1; then
            backup_size=$(numfmt --to=iec-i --suffix=B --format="%.1f" "$(stat -c%s "$backup_filename" 2>/dev/null || stat -f%z "$backup_filename")")
        else
            backup_size="$(du -h "$backup_filename" | cut -f1)"
        fi
        print_success "Current database backed up to: $backup_filename ($backup_size)"
    else
        print_error "Failed to create backup of current database"
        exit 1
    fi
}

# Function to perform the database restore
perform_restore() {
    local backup_file="$1"
    
    print_status "Starting database restore..."
    print_status "Source: $backup_file"
    print_status "Target: $DATABASE_PATH"
    
    # Create database directory if it doesn't exist
    local db_dir=$(dirname "$DATABASE_PATH")
    if [[ ! -d "$db_dir" ]]; then
        mkdir -p "$db_dir"
        print_status "Created database directory: $db_dir"
    fi
    
    # Copy backup to database location
    cp "$backup_file" "$DATABASE_PATH"
    
    # Verify the restored database
    if [[ -f "$DATABASE_PATH" ]]; then
        print_success "Database file restored successfully"
        
        # Test database integrity
        if sqlite3 "$DATABASE_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
            print_success "Restored database integrity check passed"
        else
            print_error "Restored database integrity check failed"
            exit 1
        fi
        
        # Show basic statistics
        local db_size
        if command -v numfmt >/dev/null 2>&1; then
            db_size=$(numfmt --to=iec-i --suffix=B --format="%.1f" "$(stat -c%s "$DATABASE_PATH" 2>/dev/null || stat -f%z "$DATABASE_PATH")")
        else
            db_size="$(du -h "$DATABASE_PATH" | cut -f1)"
        fi
        
        local table_count=$(sqlite3 "$DATABASE_PATH" ".tables" | wc -w)
        print_status "Restored database size: $db_size"
        print_status "Number of tables: $table_count"
        
    else
        print_error "Database restore failed - file not found after copy"
        exit 1
    fi
}

# Function to show restore summary
show_restore_summary() {
    local backup_file="$1"
    
    print_success "Database restore completed successfully!"
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                     Restore Summary                         ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} Source:      $(basename "$backup_file")${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} Target:      $DATABASE_PATH${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} Completed:   $(date '+%Y-%m-%d %H:%M:%S')${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Show table summary if possible
    if command -v sqlite3 >/dev/null 2>&1; then
        print_status "Database table summary:"
        sqlite3 "$DATABASE_PATH" "
            SELECT 
                name as table_name,
                (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as exists
            FROM sqlite_master m 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        " 2>/dev/null || print_warning "Could not query database tables"
    fi
    
    echo
    print_status "You may need to restart the application to recognize the restored database"
}

# Function to confirm restore operation
confirm_restore() {
    local backup_file="$1"
    
    if [[ "$FORCE" == true ]]; then
        return
    fi
    
    echo
    print_warning "Database restore will replace the current database!"
    print_status "Current database: $DATABASE_PATH"
    print_status "Backup file: $backup_file"
    echo
    
    if [[ -f "$DATABASE_PATH" ]]; then
        local current_size
        if command -v numfmt >/dev/null 2>&1; then
            current_size=$(numfmt --to=iec-i --suffix=B --format="%.1f" "$(stat -c%s "$DATABASE_PATH" 2>/dev/null || stat -f%z "$DATABASE_PATH")")
        else
            current_size="$(du -h "$DATABASE_PATH" | cut -f1)"
        fi
        print_warning "Current database size: $current_size"
    else
        print_status "No current database found - this will be a fresh restore"
    fi
    
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Restore cancelled"
        exit 0
    fi
}

# Parse command line arguments
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -v|--verify)
            VERIFY=true
            shift
            ;;
        --no-verify)
            VERIFY=false
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        --no-backup)
            CREATE_BACKUP=false
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                print_error "Multiple backup files specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if backup file was provided
if [[ -z "$BACKUP_FILE" ]]; then
    print_error "No backup file specified"
    echo
    echo "Usage: $0 BACKUP_FILE [OPTIONS]"
    echo "Use --help for more information"
    exit 1
fi

# Main restore process
main() {
    print_status "NeuroBridgeEDU Database Restore Starting..."
    echo
    
    # Validate backup file
    validate_backup_file "$BACKUP_FILE"
    
    # Verify backup integrity
    verify_backup_integrity "$BACKUP_FILE"
    
    # Confirm restore operation
    confirm_restore "$BACKUP_FILE"
    
    # Create backup of current database
    create_current_backup
    
    # Perform the restore
    perform_restore "$BACKUP_FILE"
    
    # Show restore summary
    show_restore_summary "$BACKUP_FILE"
}

# Run main function
main "$@"