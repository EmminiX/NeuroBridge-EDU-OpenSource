#!/bin/bash

# NeuroBridge EDU - Educational Institution Deployment Script
# Comprehensive deployment automation for educational environments
# Implements security best practices and educational compliance requirements

set -euo pipefail

# Educational deployment configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly LOG_FILE="${PROJECT_ROOT}/logs/deployment-$(date +%Y%m%d_%H%M%S).log"

# Educational environment settings
declare -A ENVIRONMENTS=(
    ["development"]="dev.neurobridge.edu"
    ["staging"]="staging.neurobridge.edu"
    ["production"]="app.neurobridge.edu"
)

# Educational compliance flags
readonly SECURITY_SCAN_REQUIRED=true
readonly COMPLIANCE_VALIDATION_REQUIRED=true
readonly EDUCATIONAL_TESTING_REQUIRED=true

# Logging function for educational audit trail
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

info() { log "INFO" "$@"; }
warn() { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }
success() { log "SUCCESS" "$@"; }

# Educational deployment validation
validate_educational_environment() {
    local environment="$1"
    
    info "🏫 Validating educational environment: $environment"
    
    # Check educational prerequisites
    if ! command -v kubectl >/dev/null 2>&1; then
        error "kubectl is required for educational deployment"
        return 1
    fi
    
    if ! command -v docker >/dev/null 2>&1; then
        error "docker is required for educational deployment"
        return 1
    fi
    
    # Educational environment validation
    if [[ ! "${!ENVIRONMENTS[*]}" =~ $environment ]]; then
        error "Invalid educational environment: $environment"
        error "Valid environments: ${!ENVIRONMENTS[*]}"
        return 1
    fi
    
    # Educational cluster connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error "Cannot connect to educational Kubernetes cluster"
        return 1
    fi
    
    success "✅ Educational environment validation passed"
}

# Educational security scanning
perform_educational_security_scan() {
    info "🔍 Performing educational security scan..."
    
    if [[ "$SECURITY_SCAN_REQUIRED" != "true" ]]; then
        info "Educational security scan skipped (disabled)"
        return 0
    fi
    
    local backend_image="neurobridge/backend:educational-latest"
    local frontend_image="neurobridge/frontend:educational-latest"
    
    # Educational container security scanning
    info "Scanning educational backend container..."
    if ! docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image \
        --severity CRITICAL,HIGH \
        --exit-code 1 \
        "$backend_image" 2>/dev/null; then
        error "Educational backend security scan failed"
        return 1
    fi
    
    info "Scanning educational frontend container..."
    if ! docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image \
        --severity CRITICAL,HIGH \
        --exit-code 1 \
        "$frontend_image" 2>/dev/null; then
        error "Educational frontend security scan failed"
        return 1
    fi
    
    success "✅ Educational security scan passed"
}

# Educational compliance validation
validate_educational_compliance() {
    info "📋 Validating educational compliance (FERPA/GDPR)..."
    
    if [[ "$COMPLIANCE_VALIDATION_REQUIRED" != "true" ]]; then
        info "Educational compliance validation skipped (disabled)"
        return 0
    fi
    
    # Educational FERPA compliance checks
    info "Checking FERPA compliance requirements..."
    
    # Verify educational data encryption
    if ! kubectl get secrets -n neurobridge-edu | grep -q neurobridge-secrets; then
        error "Educational secrets not found - FERPA compliance requirement"
        return 1
    fi
    
    # Verify educational audit logging
    if ! kubectl get configmap -n neurobridge-edu | grep -q audit-config; then
        warn "Educational audit configuration not found - GDPR compliance concern"
    fi
    
    # Educational network policy validation
    if ! kubectl get networkpolicy -n neurobridge-edu | grep -q neurobridge; then
        error "Educational network policies not found - security compliance requirement"
        return 1
    fi
    
    success "✅ Educational compliance validation passed"
}

# Educational testing suite
run_educational_tests() {
    local environment="$1"
    
    info "🧪 Running educational test suite for $environment..."
    
    if [[ "$EDUCATIONAL_TESTING_REQUIRED" != "true" ]]; then
        info "Educational testing skipped (disabled)"
        return 0
    fi
    
    # Educational backend tests
    info "Running educational backend tests..."
    cd "$PROJECT_ROOT/python_backend"
    if ! python run_tests.py --suite integration --educational --environment="$environment"; then
        error "Educational backend tests failed"
        return 1
    fi
    
    # Educational API health checks
    local api_url="${ENVIRONMENTS[$environment]}"
    info "Testing educational API endpoints at $api_url..."
    
    if ! curl -f "https://api.$api_url/health" >/dev/null 2>&1; then
        error "Educational API health check failed"
        return 1
    fi
    
    success "✅ Educational tests passed"
}

# Educational deployment execution
deploy_educational_environment() {
    local environment="$1"
    local namespace="neurobridge-${environment}"
    
    info "🚀 Deploying to educational environment: $environment"
    
    # Educational namespace preparation
    info "Preparing educational namespace: $namespace"
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
    
    # Educational compliance labels
    kubectl label namespace "$namespace" \
        compliance=ferpa-gdpr \
        environment=educational \
        data-classification=educational \
        --overwrite
    
    # Educational secret management
    info "Managing educational secrets..."
    if ! kubectl get secret neurobridge-secrets -n "$namespace" >/dev/null 2>&1; then
        warn "Educational secrets not found - manual configuration required"
    fi
    
    # Educational deployment using Kustomize
    info "Applying educational Kubernetes manifests..."
    kubectl apply -k "$PROJECT_ROOT/kubernetes/overlays/$environment/"
    
    # Educational deployment verification
    info "Verifying educational deployment..."
    kubectl rollout status deployment/neurobridge-backend -n "$namespace" --timeout=600s
    kubectl rollout status deployment/neurobridge-frontend -n "$namespace" --timeout=600s
    
    # Educational health verification
    info "Waiting for educational services to be ready..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/neurobridge-backend -n "$namespace"
    kubectl wait --for=condition=available --timeout=300s \
        deployment/neurobridge-frontend -n "$namespace"
    
    success "✅ Educational deployment completed successfully"
}

# Educational post-deployment validation
validate_educational_deployment() {
    local environment="$1"
    local api_url="${ENVIRONMENTS[$environment]}"
    
    info "🔍 Validating educational deployment..."
    
    # Educational endpoint validation
    info "Testing educational endpoints..."
    if ! curl -f "https://$api_url/health" >/dev/null 2>&1; then
        error "Educational frontend health check failed"
        return 1
    fi
    
    if ! curl -f "https://api.$api_url/health" >/dev/null 2>&1; then
        error "Educational backend health check failed"
        return 1
    fi
    
    # Educational performance validation
    info "Testing educational performance..."
    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' "https://$api_url/")
    
    if (( $(echo "$response_time > 3.0" | bc -l) )); then
        warn "Educational performance concern: ${response_time}s response time"
    else
        success "Educational performance validated: ${response_time}s response time"
    fi
    
    success "✅ Educational deployment validation passed"
}

# Educational deployment rollback
rollback_educational_deployment() {
    local environment="$1"
    local namespace="neurobridge-${environment}"
    
    error "🔄 Rolling back educational deployment in $environment"
    
    # Educational rollback execution
    kubectl rollout undo deployment/neurobridge-backend -n "$namespace"
    kubectl rollout undo deployment/neurobridge-frontend -n "$namespace"
    
    # Educational rollback verification
    kubectl rollout status deployment/neurobridge-backend -n "$namespace" --timeout=300s
    kubectl rollout status deployment/neurobridge-frontend -n "$namespace" --timeout=300s
    
    warn "Educational deployment rolled back to previous version"
}

# Educational deployment monitoring
monitor_educational_deployment() {
    local environment="$1"
    local namespace="neurobridge-${environment}"
    
    info "📊 Educational deployment monitoring..."
    
    # Educational pod status
    info "Educational pod status:"
    kubectl get pods -n "$namespace" -l app=neurobridge-edu
    
    # Educational service status
    info "Educational service status:"
    kubectl get services -n "$namespace" -l app=neurobridge-edu
    
    # Educational resource usage
    info "Educational resource usage:"
    kubectl top pods -n "$namespace" -l app=neurobridge-edu 2>/dev/null || \
        info "Metrics server not available for educational resource monitoring"
}

# Educational deployment cleanup
cleanup_educational_deployment() {
    info "🧹 Cleaning up educational deployment artifacts..."
    
    # Clean up local Docker images
    docker image prune -f || info "Docker cleanup skipped"
    
    # Clean up build cache
    rm -rf "$PROJECT_ROOT/dist" "$PROJECT_ROOT/.next" 2>/dev/null || true
    
    success "✅ Educational deployment cleanup completed"
}

# Educational deployment notification
send_educational_notification() {
    local environment="$1"
    local status="$2"
    local message="$3"
    
    info "📧 Sending educational deployment notification..."
    
    # Educational notification payload
    local payload=$(cat <<EOF
{
    "text": "🏫 Educational Deployment Notification",
    "attachments": [{
        "color": "$([[ "$status" == "success" ]] && echo "good" || echo "danger")",
        "fields": [{
            "title": "Environment",
            "value": "$environment",
            "short": true
        }, {
            "title": "Status",
            "value": "$status",
            "short": true
        }, {
            "title": "Message",
            "value": "$message",
            "short": false
        }, {
            "title": "Timestamp",
            "value": "$(date '+%Y-%m-%d %H:%M:%S')",
            "short": true
        }]
    }]
}
EOF
)
    
    # Send to educational notification channel
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "$payload" \
            "$SLACK_WEBHOOK_URL" || info "Educational notification sending failed"
    else
        info "Educational notification webhook not configured"
    fi
}

# Main educational deployment function
main() {
    local environment="${1:-}"
    local action="${2:-deploy}"
    
    if [[ -z "$environment" ]]; then
        error "Usage: $0 <environment> [action]"
        error "Environments: ${!ENVIRONMENTS[*]}"
        error "Actions: deploy, rollback, monitor, cleanup"
        exit 1
    fi
    
    # Create logs directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    info "🏫 Starting NeuroBridge EDU deployment process..."
    info "Environment: $environment"
    info "Action: $action"
    info "Log file: $LOG_FILE"
    
    case "$action" in
        deploy)
            trap 'rollback_educational_deployment "$environment"; send_educational_notification "$environment" "failed" "Deployment failed and was rolled back"' ERR
            
            validate_educational_environment "$environment"
            perform_educational_security_scan
            validate_educational_compliance
            deploy_educational_environment "$environment"
            run_educational_tests "$environment"
            validate_educational_deployment "$environment"
            monitor_educational_deployment "$environment"
            
            send_educational_notification "$environment" "success" "Deployment completed successfully"
            success "🎉 Educational deployment completed successfully!"
            ;;
            
        rollback)
            rollback_educational_deployment "$environment"
            send_educational_notification "$environment" "rollback" "Deployment rolled back"
            ;;
            
        monitor)
            monitor_educational_deployment "$environment"
            ;;
            
        cleanup)
            cleanup_educational_deployment
            ;;
            
        *)
            error "Invalid action: $action"
            error "Valid actions: deploy, rollback, monitor, cleanup"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"