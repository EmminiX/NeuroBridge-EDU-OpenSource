#!/bin/bash

# NeuroBridgeEDU Database Backup Script
# 
# This script creates backups of the SQLite database with timestamps
# and provides options for different backup strategies.
#
# Usage:
#   ./scripts/backup-db.sh [options]
#
# Options:
#   -f, --full      Create full backup (default)
#   -i, --incremental  Create incremental backup (not implemented yet)
#   -c, --compress  Compress backup file with gzip
#   -r, --rotate    Rotate old backups (keep last N)
#   -d, --directory Backup directory (default: ./backups)
#   -h, --help      Show this help message

set -euo pipefail

# Default configuration
BACKUP_DIR="./backups"
DATABASE_PATH="${DATABASE_PATH:-./data/neurobridge.db}"
COMPRESS=false
ROTATE=false
KEEP_BACKUPS=7
BACKUP_TYPE="full"

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
NeuroBridgeEDU Database Backup Script

Usage: $0 [OPTIONS]

OPTIONS:
    -f, --full          Create full backup (default)
    -c, --compress      Compress backup with gzip
    -r, --rotate        Rotate old backups (keep last $KEEP_BACKUPS)
    -d, --directory     Backup directory (default: $BACKUP_DIR)
    -k, --keep          Number of backups to keep when rotating (default: $KEEP_BACKUPS)
    -h, --help          Show this help message

EXAMPLES:
    $0                  # Create simple backup
    $0 -c -r           # Create compressed backup and rotate old ones
    $0 -d /path/to/backups -k 14  # Custom directory, keep 14 backups

ENVIRONMENT VARIABLES:
    DATABASE_PATH       Path to SQLite database (default: $DATABASE_PATH)

EOF
}

# Function to create backup directory
create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        print_status "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

# Function to check if database exists and is accessible
check_database() {
    if [[ ! -f "$DATABASE_PATH" ]]; then
        print_error "Database file not found: $DATABASE_PATH"
        exit 1
    fi

    if [[ ! -r "$DATABASE_PATH" ]]; then
        print_error "Database file not readable: $DATABASE_PATH"
        exit 1
    fi

    # Check if database is valid SQLite file
    if ! sqlite3 "$DATABASE_PATH" "SELECT 1;" > /dev/null 2>&1; then
        print_error "Database file appears to be corrupted: $DATABASE_PATH"
        exit 1
    fi

    print_status "Database validation passed: $DATABASE_PATH"
}

# Function to create backup filename
create_backup_filename() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local hostname=$(hostname -s)
    local basename="neurobridge_${timestamp}_${hostname}"
    
    if [[ "$COMPRESS" == true ]]; then
        echo "${BACKUP_DIR}/${basename}.db.gz"
    else
        echo "${BACKUP_DIR}/${basename}.db"
    fi
}

# Function to get database size in human readable format
get_db_size() {
    if command -v numfmt >/dev/null 2>&1; then
        numfmt --to=iec-i --suffix=B --format="%.1f" "$(stat -c%s "$DATABASE_PATH" 2>/dev/null || stat -f%z "$DATABASE_PATH")"
    else
        echo "$(du -h "$DATABASE_PATH" | cut -f1)"
    fi
}

# Function to create the backup
create_backup() {
    local backup_file="$1"
    local start_time=$(date +%s)
    
    print_status "Starting backup process..."
    print_status "Source: $DATABASE_PATH ($(get_db_size))"
    print_status "Target: $backup_file"

    # Create backup using SQLite's backup command for consistency
    if [[ "$COMPRESS" == true ]]; then
        # Create compressed backup
        sqlite3 "$DATABASE_PATH" ".backup /dev/stdout" | gzip > "$backup_file"
    else
        # Create uncompressed backup
        sqlite3 "$DATABASE_PATH" ".backup $backup_file"
    fi

    # Verify backup was created successfully
    if [[ ! -f "$backup_file" ]]; then
        print_error "Backup file was not created: $backup_file"
        exit 1
    fi

    # Calculate backup time and size
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local backup_size
    
    if command -v numfmt >/dev/null 2>&1; then
        backup_size=$(numfmt --to=iec-i --suffix=B --format="%.1f" "$(stat -c%s "$backup_file" 2>/dev/null || stat -f%z "$backup_file")")
    else
        backup_size="$(du -h "$backup_file" | cut -f1)"
    fi

    print_success "Backup completed successfully in ${duration}s"
    print_success "Backup file: $backup_file ($backup_size)"

    # Test backup integrity if not compressed
    if [[ "$COMPRESS" == false ]]; then
        print_status "Verifying backup integrity..."
        if sqlite3 "$backup_file" "PRAGMA integrity_check;" | grep -q "ok"; then
            print_success "Backup integrity verification passed"
        else
            print_error "Backup integrity verification failed"
            exit 1
        fi
    fi
}

# Function to rotate old backups
rotate_backups() {
    print_status "Rotating backups (keeping last $KEEP_BACKUPS)..."
    
    # Find backup files (both compressed and uncompressed)
    local backup_files=($(ls -t "$BACKUP_DIR"/neurobridge_*.db* 2>/dev/null || true))
    local total_backups=${#backup_files[@]}
    
    if [[ $total_backups -le $KEEP_BACKUPS ]]; then
        print_status "No rotation needed (found $total_backups backups, keeping $KEEP_BACKUPS)"
        return
    fi

    # Remove old backups
    local removed_count=0
    for ((i=$KEEP_BACKUPS; i<$total_backups; i++)); do
        local old_backup="${backup_files[$i]}"
        print_status "Removing old backup: $(basename "$old_backup")"
        rm -f "$old_backup"
        ((removed_count++))
    done

    print_success "Removed $removed_count old backup(s)"
}

# Function to show backup statistics
show_backup_stats() {
    print_status "Backup Statistics:"
    echo "  Database: $DATABASE_PATH"
    echo "  Backup Directory: $BACKUP_DIR"
    echo "  Backup Type: $BACKUP_TYPE"
    echo "  Compression: $COMPRESS"
    echo "  Rotation: $ROTATE"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_count=$(ls -1 "$BACKUP_DIR"/neurobridge_*.db* 2>/dev/null | wc -l)
        local total_size
        
        if command -v du >/dev/null 2>&1; then
            total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "unknown")
        else
            total_size="unknown"
        fi
        
        echo "  Existing Backups: $backup_count"
        echo "  Total Backup Size: $total_size"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--full)
            BACKUP_TYPE="full"
            shift
            ;;
        -c|--compress)
            COMPRESS=true
            shift
            ;;
        -r|--rotate)
            ROTATE=true
            shift
            ;;
        -d|--directory)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -k|--keep)
            KEEP_BACKUPS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "NeuroBridgeEDU Database Backup Starting..."
    
    # Validate inputs
    if [[ ! "$KEEP_BACKUPS" =~ ^[0-9]+$ ]] || [[ "$KEEP_BACKUPS" -lt 1 ]]; then
        print_error "Invalid keep count: $KEEP_BACKUPS (must be positive integer)"
        exit 1
    fi

    show_backup_stats
    echo

    # Create backup directory
    create_backup_dir

    # Check database
    check_database

    # Create backup
    local backup_file=$(create_backup_filename)
    create_backup "$backup_file"

    # Rotate backups if requested
    if [[ "$ROTATE" == true ]]; then
        rotate_backups
    fi

    echo
    print_success "Backup process completed successfully!"
    print_status "Backup location: $backup_file"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi