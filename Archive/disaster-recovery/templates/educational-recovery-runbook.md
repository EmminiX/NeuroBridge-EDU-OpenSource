# NeuroBridge EDU - Educational Recovery Runbook

## Quick Reference - Emergency Contacts

**Educational Emergency Hotline:** +1-800-EDU-HELP (800-338-4357)  
**DevOps On-Call:** PagerDuty Auto-Escalation  
**Educational IT Director:** [Contact via emergency hotline]  
**Compliance Officer:** [Contact via emergency hotline]

---

## 🚨 IMMEDIATE RESPONSE CHECKLIST

### Step 1: Initial Assessment (0-2 minutes)
- [ ] **Confirm outage scope**: Single institution or widespread?
- [ ] **Check monitoring dashboards**: Grafana at https://monitoring.neurobridge.edu
- [ ] **Verify alert accuracy**: False positive or genuine issue?
- [ ] **Activate incident commander**: Assign educational incident lead

### Step 2: Emergency Communication (2-5 minutes)
- [ ] **Update status page**: https://status.neurobridge.edu
- [ ] **Notify educational stakeholders**: Use emergency contact list
- [ ] **Join incident channel**: Slack #edu-emergency
- [ ] **Start incident log**: Document all actions with timestamps

---

## 🏫 EDUCATIONAL SERVICE RECOVERY PROCEDURES

### Scenario A: Backend Service Down (RTO: 5 minutes)

**Symptoms:**
- Students cannot access transcription services
- API health checks failing: `curl https://api.neurobridge.edu/health`
- Prometheus alert: `EducationalBackendDown`

**Immediate Actions:**
```bash
# 1. Check pod status
kubectl get pods -n neurobridge-edu -l component=backend

# 2. Scale up pods immediately
kubectl scale deployment neurobridge-backend -n neurobridge-edu --replicas=5

# 3. Check recent logs
kubectl logs -n neurobridge-edu deployment/neurobridge-backend --tail=100

# 4. Restart if needed
kubectl rollout restart deployment/neurobridge-backend -n neurobridge-edu

# 5. Monitor recovery
kubectl rollout status deployment/neurobridge-backend -n neurobridge-edu
```

**Validation:**
```bash
# Test educational endpoints
curl https://api.neurobridge.edu/health
curl https://api.neurobridge.edu/api/transcription/config
```

### Scenario B: Database Issues (RTO: 30 minutes)

**Symptoms:**
- Database connection errors
- Student authentication failures
- API key retrieval failures

**Immediate Actions:**
```bash
# 1. Check database pod
kubectl get pods -n neurobridge-edu -l component=database

# 2. Check database connectivity
kubectl exec -n neurobridge-edu deployment/neurobridge-backend -- \
  pg_isready -h database -U neurobridge

# 3. Review database logs
kubectl logs -n neurobridge-edu deployment/database --tail=100

# 4. If corruption suspected, initiate recovery
./disaster-recovery/scripts/educational-db-restore.sh production latest
```

### Scenario C: Complete Infrastructure Failure (RTO: 60 minutes)

**Symptoms:**
- Multiple services down
- Kubernetes cluster unreachable
- DNS resolution failures

**Immediate Actions:**
```bash
# 1. Activate disaster recovery site
./disaster-recovery/scripts/educational-failover.sh activate

# 2. Check cluster status
kubectl cluster-info
kubectl get nodes

# 3. If cluster down, use backup cluster
export KUBECONFIG=/path/to/backup-cluster-config
kubectl apply -k kubernetes/overlays/production/
```

---

## 📊 EDUCATIONAL MONITORING COMMANDS

### Health Check Commands
```bash
# Overall system health
curl https://app.neurobridge.edu/health
curl https://api.neurobridge.edu/health

# Educational service status
kubectl get pods -n neurobridge-edu
kubectl get services -n neurobridge-edu
kubectl top pods -n neurobridge-edu

# Database health
kubectl exec -n neurobridge-edu deployment/neurobridge-backend -- \
  psql -h database -U neurobridge -d neurobridge_edu -c "SELECT 1;"
```

### Performance Monitoring
```bash
# Response time check
time curl https://api.neurobridge.edu/health

# Load testing (be cautious in production)
ab -n 10 -c 2 https://app.neurobridge.edu/

# Resource usage
kubectl top nodes
kubectl describe node [NODE_NAME]
```

---

## 🔐 EDUCATIONAL SECURITY PROCEDURES

### API Key Recovery
```bash
# Check API key service
kubectl get pods -n neurobridge-edu -l component=backend
kubectl exec -n neurobridge-edu deployment/neurobridge-backend -- \
  curl -f http://localhost:3939/api/api-keys/list

# Verify encryption service
kubectl get secrets -n neurobridge-edu neurobridge-secrets
```

### Educational Authentication Issues
```bash
# Check authentication flow
kubectl logs -n neurobridge-edu deployment/neurobridge-backend | grep -i auth

# Verify JWT secret
kubectl get secret neurobridge-secrets -n neurobridge-edu -o yaml
```

---

## 📋 EDUCATIONAL COMPLIANCE PROCEDURES

### FERPA Incident Response
1. **Immediate containment**: Stop any unauthorized data access
2. **Impact assessment**: Determine scope of student data exposure
3. **Notification timeline**: 
   - Internal: Immediate
   - Educational institutions: Within 2 hours
   - Students/Parents: Within 24 hours (if required)
4. **Documentation**: Complete incident report for educational records

### GDPR Incident Response
1. **Breach assessment**: Determine if personal data is at risk
2. **72-hour notification**: To supervisory authority if high risk
3. **Data subject notification**: If high risk to rights and freedoms
4. **Remediation actions**: Technical and organizational measures

---

## 🧪 EDUCATIONAL TESTING PROCEDURES

### Post-Recovery Validation
```bash
# Educational functionality test
./scripts/educational-smoke-test.sh

# Performance validation
./scripts/educational-performance-test.sh

# Security validation
./scripts/educational-security-check.sh
```

### Sample Educational Test Script
```bash
#!/bin/bash
# Educational service validation

echo "Testing educational endpoints..."

# Test frontend
if curl -f https://app.neurobridge.edu/health; then
    echo "✅ Frontend healthy"
else
    echo "❌ Frontend unhealthy"
fi

# Test backend API
if curl -f https://api.neurobridge.edu/health; then
    echo "✅ Backend API healthy"
else
    echo "❌ Backend API unhealthy"
fi

# Test transcription config
if curl -f https://api.neurobridge.edu/api/transcription/config; then
    echo "✅ Transcription service healthy"
else
    echo "❌ Transcription service unhealthy"
fi
```

---

## 📧 EDUCATIONAL COMMUNICATION TEMPLATES

### Student Notification Template
```
Subject: NeuroBridge EDU Service Update - [STATUS]

Dear Students,

We are currently experiencing [BRIEF_DESCRIPTION] with the NeuroBridge EDU transcription service.

Impact: [SPECIFIC_IMPACT_ON_STUDENTS]
Estimated Resolution: [TIME_ESTIMATE]
Alternative Options: [IF_ANY]

We apologize for any inconvenience and are working to resolve this quickly.

Updates: https://status.neurobridge.edu
Support: support@neurobridge.edu

NeuroBridge EDU Team
```

### Faculty Notification Template
```
Subject: NeuroBridge EDU Technical Issue - Immediate Action Required

Faculty and Staff,

NeuroBridge EDU is experiencing [TECHNICAL_ISSUE]. 

For lectures scheduled in the next [TIME_PERIOD]:
- [ALTERNATIVE_OPTION_1]
- [ALTERNATIVE_OPTION_2]
- [BACKUP_PROCEDURE]

We expect resolution by [TIME_ESTIMATE].

Questions: Contact your IT department or call 800-EDU-HELP

Educational Technology Team
```

---

## 📈 EDUCATIONAL ESCALATION MATRIX

| Time Elapsed | Escalation Level | Actions |
|--------------|------------------|---------|
| 0-5 minutes | **Level 1** | DevOps team responds, initial troubleshooting |
| 5-15 minutes | **Level 2** | Educational IT Director notified, stakeholder updates |
| 15-30 minutes | **Level 3** | Executive team notified, vendor escalation |
| 30+ minutes | **Level 4** | Public communications, disaster recovery activation |

---

## 🔄 EDUCATIONAL RECOVERY VALIDATION

### Recovery Acceptance Criteria
- [ ] All educational services responding within 2 seconds
- [ ] Student authentication working for test accounts
- [ ] Transcription services functional with sample audio
- [ ] API key management operational
- [ ] Educational monitoring dashboards green
- [ ] Compliance audit logging active

### Educational Stakeholder Sign-off
- [ ] DevOps Team Lead: _________________
- [ ] Educational IT Director: _________________
- [ ] Security/Compliance Officer: _________________
- [ ] Product Owner: _________________

---

## 📚 EDUCATIONAL REFERENCE LINKS

- **Monitoring Dashboard**: https://monitoring.neurobridge.edu
- **Status Page**: https://status.neurobridge.edu
- **Educational Documentation**: https://docs.neurobridge.edu
- **Kubernetes Dashboard**: [Internal Link]
- **Log Aggregation**: [Internal Link]
- **Compliance Procedures**: [Internal Link]

---

**Last Updated:** [DATE]  
**Next Review:** [QUARTERLY]  
**Document Owner:** Educational DevOps Team