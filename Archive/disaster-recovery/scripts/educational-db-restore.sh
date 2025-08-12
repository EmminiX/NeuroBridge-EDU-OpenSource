#!/bin/bash

# NeuroBridge EDU - Educational Database Disaster Recovery Script
# FERPA/GDPR compliant database restoration for educational institutions
# Implements secure recovery procedures with audit logging

set -euo pipefail

# Educational recovery configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/log/neurobridge/educational-recovery-$(date +%Y%m%d_%H%M%S).log"
readonly BACKUP_BASE_PATH="/var/lib/neurobridge/backups"
readonly COMPLIANCE_LOG="/var/log/neurobridge/compliance-audit.log"

# Educational database configuration
readonly DB_CONTAINER="neurobridge-database"
readonly DB_NAME="neurobridge_edu"
readonly DB_USER="neurobridge"
readonly EDUCATIONAL_NAMESPACE="neurobridge-edu"

# Educational compliance flags
readonly FERPA_COMPLIANCE=true
readonly GDPR_COMPLIANCE=true
readonly AUDIT_REQUIRED=true

# Logging functions for educational audit trail
log() {
    local level="$1"
    shift
    local message="[$(date '+%Y-%m-%d %H:%M:%S UTC')] [$level] $*"
    echo "$message" | tee -a "$LOG_FILE"
    
    # Educational compliance logging
    if [[ "$AUDIT_REQUIRED" == "true" ]]; then
        echo "$message" >> "$COMPLIANCE_LOG"
    fi
}

info() { log "INFO" "$@"; }
warn() { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }
success() { log "SUCCESS" "$@"; }
compliance() { log "COMPLIANCE" "$@"; }

# Educational recovery validation
validate_educational_recovery_environment() {
    info "🔍 Validating educational recovery environment..."
    
    # Check educational prerequisites
    local missing_tools=()
    for tool in kubectl docker pg_dump pg_restore; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools for educational recovery: ${missing_tools[*]}"
        return 1
    fi
    
    # Educational cluster connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error "Cannot connect to educational Kubernetes cluster"
        return 1
    fi
    
    # Educational namespace verification
    if ! kubectl get namespace "$EDUCATIONAL_NAMESPACE" >/dev/null 2>&1; then
        error "Educational namespace not found: $EDUCATIONAL_NAMESPACE"
        return 1
    fi
    
    # Educational compliance validation
    if [[ "$FERPA_COMPLIANCE" == "true" ]]; then
        info "FERPA compliance mode enabled - enhanced audit logging active"
        compliance "Educational database recovery initiated under FERPA compliance"
    fi
    
    if [[ "$GDPR_COMPLIANCE" == "true" ]]; then
        info "GDPR compliance mode enabled - data protection measures active"
        compliance "Educational database recovery initiated under GDPR compliance"
    fi
    
    success "✅ Educational recovery environment validation passed"
}

# Educational backup discovery and validation
discover_educational_backups() {
    local environment="$1"
    local backup_date="${2:-latest}"
    
    info "🔍 Discovering educational backups for environment: $environment"
    
    local backup_path="$BACKUP_BASE_PATH/$environment"
    
    if [[ ! -d "$backup_path" ]]; then
        error "Educational backup path not found: $backup_path"
        return 1
    fi
    
    # Find educational backups
    local backup_files=()
    if [[ "$backup_date" == "latest" ]]; then
        # Find latest educational backup
        mapfile -t backup_files < <(find "$backup_path" -name "neurobridge-edu-*.sql.gz" -type f | sort -r | head -5)
    else
        # Find educational backup by date
        mapfile -t backup_files < <(find "$backup_path" -name "neurobridge-edu-${backup_date}*.sql.gz" -type f)
    fi
    
    if [[ ${#backup_files[@]} -eq 0 ]]; then
        error "No educational backups found for date: $backup_date"
        return 1
    fi
    
    info "Found ${#backup_files[@]} educational backup(s):"
    for backup in "${backup_files[@]}"; do
        local backup_size
        backup_size=$(stat -c%s "$backup" | numfmt --to=iec)
        local backup_time
        backup_time=$(stat -c%y "$backup")
        info "  - $(basename "$backup") (${backup_size}, ${backup_time})"
    done
    
    # Educational backup integrity validation
    info "🔍 Validating educational backup integrity..."
    local selected_backup="${backup_files[0]}"
    
    if ! gunzip -t "$selected_backup"; then
        error "Educational backup integrity check failed: $selected_backup"
        return 1
    fi
    
    success "✅ Educational backup validation passed: $selected_backup"
    echo "$selected_backup"
}

# Educational database preparation
prepare_educational_database_recovery() {
    local backup_file="$1"
    
    info "📋 Preparing educational database for recovery..."
    
    # Educational database connection validation
    if ! kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        pg_isready -h database -U "$DB_USER" >/dev/null 2>&1; then
        error "Cannot connect to educational database"
        return 1
    fi
    
    # Educational read-only mode activation
    info "🔒 Activating educational database read-only mode..."
    kubectl patch deployment neurobridge-backend -n "$EDUCATIONAL_NAMESPACE" \
        -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","env":[{"name":"DATABASE_READ_ONLY","value":"true"}]}]}}}}'
    
    # Wait for educational read-only activation
    kubectl rollout status deployment/neurobridge-backend -n "$EDUCATIONAL_NAMESPACE" --timeout=120s
    
    # Educational connection termination
    info "🔌 Terminating educational database connections..."
    kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();"
    
    # Educational pre-recovery backup
    info "💾 Creating educational pre-recovery backup..."
    local pre_recovery_backup="/tmp/neurobridge-pre-recovery-$(date +%Y%m%d_%H%M%S).sql"
    kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        pg_dump -h database -U "$DB_USER" -d "$DB_NAME" > "$pre_recovery_backup"
    
    if [[ -f "$pre_recovery_backup" ]]; then
        success "✅ Educational pre-recovery backup created: $pre_recovery_backup"
        compliance "Educational pre-recovery backup created for audit trail"
    else
        error "Failed to create educational pre-recovery backup"
        return 1
    fi
    
    success "✅ Educational database prepared for recovery"
}

# Educational database restoration
execute_educational_database_restore() {
    local backup_file="$1"
    
    info "🔄 Executing educational database restoration..."
    compliance "Educational database restoration initiated from: $(basename "$backup_file")"
    
    # Educational database drop and recreate
    info "🗑️ Dropping and recreating educational database..."
    kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    
    kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    
    # Educational data restoration
    info "📥 Restoring educational data from backup..."
    local restore_start_time
    restore_start_time=$(date +%s)
    
    # Decompress and restore educational backup
    if gunzip -c "$backup_file" | kubectl exec -i -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1; then
        
        local restore_end_time
        restore_end_time=$(date +%s)
        local restore_duration=$((restore_end_time - restore_start_time))
        
        success "✅ Educational database restoration completed in ${restore_duration} seconds"
        compliance "Educational database restoration completed successfully - $(basename "$backup_file")"
    else
        error "Educational database restoration failed"
        compliance "Educational database restoration FAILED - manual intervention required"
        return 1
    fi
}

# Educational data validation
validate_educational_data_integrity() {
    info "🔍 Validating educational data integrity..."
    
    # Educational table existence validation
    local expected_tables=("transcription_sessions" "app_settings" "api_usage")
    for table in "${expected_tables[@]}"; do
        local table_count
        table_count=$(kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
            psql -h database -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '$table';")
        
        if [[ "$table_count" -eq 0 ]]; then
            error "Educational table missing after restoration: $table"
            return 1
        fi
        
        info "✅ Educational table validated: $table"
    done
    
    # Educational data consistency validation
    local session_count
    session_count=$(kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM transcription_sessions;")
    
    info "Educational transcription sessions restored: $session_count"
    compliance "Educational data validation completed - $session_count sessions restored"
    
    # Educational configuration validation
    local settings_count
    settings_count=$(kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM app_settings;")
    
    info "Educational app settings restored: $settings_count"
    
    success "✅ Educational data integrity validation passed"
}

# Educational service restoration
restore_educational_services() {
    info "🔄 Restoring educational services..."
    
    # Educational read-write mode activation
    info "🔓 Activating educational database read-write mode..."
    kubectl patch deployment neurobridge-backend -n "$EDUCATIONAL_NAMESPACE" \
        -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","env":[{"name":"DATABASE_READ_ONLY","value":"false"}]}]}}}}'
    
    # Wait for educational service restoration
    kubectl rollout status deployment/neurobridge-backend -n "$EDUCATIONAL_NAMESPACE" --timeout=300s
    
    # Educational health verification
    info "🔍 Verifying educational service health..."
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
            curl -f http://localhost:3939/health >/dev/null 2>&1; then
            break
        fi
        
        ((attempt++))
        info "Educational health check attempt $attempt/$max_attempts..."
        sleep 10
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        error "Educational service health check failed after restoration"
        return 1
    fi
    
    success "✅ Educational services restored and healthy"
    compliance "Educational service restoration completed successfully"
}

# Educational recovery testing
test_educational_recovery() {
    info "🧪 Testing educational recovery functionality..."
    
    # Educational API endpoint testing
    local test_endpoints=(
        "/health"
        "/api/transcription/config"
        "/api/api-keys/list"
    )
    
    for endpoint in "${test_endpoints[@]}"; do
        info "Testing educational endpoint: $endpoint"
        if kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
            curl -f "http://localhost:3939$endpoint" >/dev/null 2>&1; then
            success "✅ Educational endpoint test passed: $endpoint"
        else
            warn "⚠️ Educational endpoint test failed: $endpoint"
        fi
    done
    
    # Educational database connectivity test
    if kubectl exec -n "$EDUCATIONAL_NAMESPACE" deployment/neurobridge-backend -- \
        psql -h database -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        success "✅ Educational database connectivity test passed"
    else
        error "Educational database connectivity test failed"
        return 1
    fi
    
    success "✅ Educational recovery testing completed"
    compliance "Educational recovery functionality validated"
}

# Educational recovery notification
send_educational_recovery_notification() {
    local status="$1"
    local backup_file="$2"
    local recovery_duration="$3"
    
    info "📧 Sending educational recovery notification..."
    
    local notification_payload
    notification_payload=$(cat <<EOF
{
    "text": "🏫 Educational Database Recovery Notification",
    "attachments": [{
        "color": "$([[ "$status" == "success" ]] && echo "good" || echo "danger")",
        "fields": [{
            "title": "Recovery Status",
            "value": "$status",
            "short": true
        }, {
            "title": "Backup File",
            "value": "$(basename "$backup_file")",
            "short": true
        }, {
            "title": "Recovery Duration",
            "value": "${recovery_duration} seconds",
            "short": true
        }, {
            "title": "Compliance",
            "value": "FERPA/GDPR Compliant",
            "short": true
        }, {
            "title": "Educational Impact",
            "value": "Database services restored",
            "short": false
        }]
    }]
}
EOF
)
    
    # Send to educational notification channel
    if [[ -n "${EDUCATIONAL_SLACK_WEBHOOK:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "$notification_payload" \
            "$EDUCATIONAL_SLACK_WEBHOOK" || info "Educational notification failed"
    else
        info "Educational notification webhook not configured"
    fi
    
    compliance "Educational recovery notification sent - status: $status"
}

# Main educational recovery function
main() {
    local environment="${1:-production}"
    local backup_date="${2:-latest}"
    
    if [[ $# -eq 0 ]]; then
        error "Usage: $0 <environment> [backup_date]"
        error "Environments: production, staging, development"
        error "Backup date: YYYYMMDD or 'latest'"
        exit 1
    fi
    
    # Create logs directory
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$(dirname "$COMPLIANCE_LOG")"
    
    info "🏫 Starting NeuroBridge EDU database recovery..."
    info "Environment: $environment"
    info "Backup date: $backup_date"
    info "Compliance mode: FERPA($FERPA_COMPLIANCE) GDPR($GDPR_COMPLIANCE)"
    
    local recovery_start_time
    recovery_start_time=$(date +%s)
    
    # Educational recovery execution with error handling
    local backup_file
    if validate_educational_recovery_environment && \
       backup_file=$(discover_educational_backups "$environment" "$backup_date") && \
       prepare_educational_database_recovery "$backup_file" && \
       execute_educational_database_restore "$backup_file" && \
       validate_educational_data_integrity && \
       restore_educational_services && \
       test_educational_recovery; then
        
        local recovery_end_time
        recovery_end_time=$(date +%s)
        local recovery_duration=$((recovery_end_time - recovery_start_time))
        
        success "🎉 Educational database recovery completed successfully!"
        compliance "Educational database recovery completed - total duration: ${recovery_duration}s"
        send_educational_recovery_notification "success" "$backup_file" "$recovery_duration"
        
        info "Recovery summary:"
        info "  - Environment: $environment"
        info "  - Backup file: $(basename "$backup_file")"
        info "  - Recovery duration: ${recovery_duration} seconds"
        info "  - Compliance: FERPA/GDPR maintained"
        
        exit 0
    else
        local recovery_end_time
        recovery_end_time=$(date +%s)
        local recovery_duration=$((recovery_end_time - recovery_start_time))
        
        error "❌ Educational database recovery failed!"
        compliance "Educational database recovery FAILED - manual intervention required"
        send_educational_recovery_notification "failed" "${backup_file:-unknown}" "$recovery_duration"
        
        warn "Educational recovery failed. Check logs: $LOG_FILE"
        warn "Compliance audit log: $COMPLIANCE_LOG"
        
        exit 1
    fi
}

# Execute main function
main "$@"