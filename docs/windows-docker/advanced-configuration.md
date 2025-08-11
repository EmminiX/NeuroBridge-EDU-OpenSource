# NeuroBridge EDU - Advanced Configuration Guide 🔧

This guide covers advanced configuration options for NeuroBridge EDU on Windows, including custom domains, SSL certificates, resource optimization, production deployment, and enterprise features.

## 📋 Table of Contents

1. [Custom Domain Setup](#custom-domain-setup)
2. [SSL Certificate Configuration](#ssl-certificate-configuration)
3. [Resource Optimization](#resource-optimization)
4. [Production Deployment](#production-deployment)
5. [Enterprise Features](#enterprise-features)
6. [Backup and Recovery](#backup-and-recovery)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Security Hardening](#security-hardening)

---

## 🌐 Custom Domain Setup

### Local Development with Custom Domain

Set up a custom local domain for easier access and development.

#### Step 1: Configure Windows Hosts File

```powershell
# Run as Administrator
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "127.0.0.1 neurobridge.local"
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "127.0.0.1 api.neurobridge.local"
```

#### Step 2: Update Docker Configuration

Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  frontend:
    environment:
      - VITE_API_BASE_URL=http://api.neurobridge.local:3939
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`neurobridge.local`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=3131"
  
  backend:
    environment:
      - CORS_ORIGINS=http://neurobridge.local,http://api.neurobridge.local
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.neurobridge.local`)"
      - "traefik.http.services.backend.loadbalancer.server.port=3939"

  traefik:
    image: traefik:v2.10
    container_name: neurobridge-proxy
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "80:80"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - neurobridge-network
```

#### Step 3: Access Application

After redeployment:
- **Frontend**: http://neurobridge.local
- **Backend API**: http://api.neurobridge.local
- **Traefik Dashboard**: http://localhost:8080

### External Domain Configuration

For external domain access (requires DNS control):

#### Step 1: DNS Configuration

Configure your DNS to point to your server:
```
A    neurobridge.yourdomain.com    -> YOUR_SERVER_IP
A    api.neurobridge.yourdomain.com -> YOUR_SERVER_IP
```

#### Step 2: Update Environment Variables

```bash
# .env
VITE_API_BASE_URL=https://api.neurobridge.yourdomain.com
CORS_ORIGINS=https://neurobridge.yourdomain.com,https://api.neurobridge.yourdomain.com
```

---

## 🔒 SSL Certificate Configuration

### Self-Signed Certificates (Development)

#### Generate Certificates

```powershell
# Create certificates directory
New-Item -ItemType Directory -Path ".\certs" -Force

# Generate private key
openssl genrsa -out .\certs\server.key 2048

# Generate certificate signing request
openssl req -new -key .\certs\server.key -out .\certs\server.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=neurobridge.local"

# Generate self-signed certificate
openssl x509 -req -days 365 -in .\certs\server.csr -signkey .\certs\server.key -out .\certs\server.crt

# Create combined certificate file
Get-Content .\certs\server.crt, .\certs\server.key | Set-Content .\certs\server.pem
```

#### Update Docker Configuration

```yaml
# docker-compose.ssl.yml
version: '3.8'

services:
  nginx-ssl:
    image: nginx:alpine
    container_name: neurobridge-ssl-proxy
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./certs:/etc/nginx/certs
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
    networks:
      - neurobridge-network

  frontend:
    environment:
      - VITE_API_BASE_URL=https://api.neurobridge.local
```

#### Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3131;
    }
    
    upstream backend {
        server backend:3939;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name neurobridge.local api.neurobridge.local;
        return 301 https://$server_name$request_uri;
    }

    # Frontend SSL
    server {
        listen 443 ssl;
        server_name neurobridge.local;
        
        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Backend SSL
    server {
        listen 443 ssl;
        server_name api.neurobridge.local;
        
        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### Let's Encrypt Certificates (Production)

#### Using Certbot with Docker

```yaml
# docker-compose.letsencrypt.yml
version: '3.8'

services:
  certbot:
    image: certbot/certbot
    container_name: neurobridge-certbot
    volumes:
      - ./letsencrypt:/etc/letsencrypt
      - ./www-certbot:/var/www/certbot
    command: certonly --webroot --webroot-path=/var/www/certbot --email your@email.com --agree-tos --no-eff-email -d neurobridge.yourdomain.com -d api.neurobridge.yourdomain.com

  nginx-ssl:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./letsencrypt:/etc/letsencrypt
      - ./www-certbot:/var/www/certbot
      - ./nginx-ssl.conf:/etc/nginx/nginx.conf
    depends_on:
      - certbot
```

#### Automatic Certificate Renewal

```powershell
# PowerShell script for certificate renewal
$renewalScript = @"
# Auto-renew certificates
docker compose -f docker-compose.letsencrypt.yml run --rm certbot renew
docker compose restart nginx-ssl
"@

$renewalScript | Out-File -FilePath ".\scripts\renew-certificates.ps1" -Encoding UTF8

# Create scheduled task for renewal
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$PWD\scripts\renew-certificates.ps1`""
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At 3am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "NeuroBridge SSL Renewal" -Description "Renew SSL certificates for NeuroBridge EDU"
```

---

## ⚡ Resource Optimization

### Docker Desktop Resource Allocation

#### Configure Docker Desktop Resources

```powershell
# PowerShell script to configure Docker Desktop resources
$dockerSettings = @{
    "memoryMiB" = 8192          # 8GB RAM
    "cpus" = 6                  # 6 CPU cores
    "diskSizeMiB" = 65536      # 64GB disk
    "swapMiB" = 2048           # 2GB swap
}

$dockerConfigPath = "$env:APPDATA\Docker\settings.json"

# Read current settings
$settings = Get-Content $dockerConfigPath | ConvertFrom-Json

# Update resource settings
$settings.memoryMiB = $dockerSettings.memoryMiB
$settings.cpus = $dockerSettings.cpus
$settings.diskSizeMiB = $dockerSettings.diskSizeMiB
$settings.swapMiB = $dockerSettings.swapMiB

# Save updated settings
$settings | ConvertTo-Json -Depth 10 | Set-Content $dockerConfigPath

Write-Host "Docker Desktop resource settings updated. Please restart Docker Desktop."
```

### Container Resource Limits

Create `docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  frontend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3131"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    restart: unless-stopped
    environment:
      - WORKERS=4  # Increase workers for production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3939/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### WSL2 Optimization

#### Configure WSL2 Resources

Create/update `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
# Processors to assign to WSL2
processors=6

# Memory to assign to WSL2 (12GB)
memory=12GB

# Swap size (4GB)
swap=4GB

# Swap file location
# swapfile=C:\\Users\\%USERNAME%\\AppData\\Local\\Temp\\swap.vhdx

# Disable page reporting (can improve performance)
pageReporting=false

# Turn on default connection to bind to the Windows localhost proxy
localhostForwarding=true

# Disables nested virtualization
nestedVirtualization=false

# Turns on output console showing contents of dmesg when opening a WSL 2 distro for debugging
debugConsole=false

# Enable experimental features
[experimental]
sparseVhd=true
networkingMode=mirrored
dnsTunneling=true
firewall=true
autoProxy=true
```

#### Optimize WSL2 File System Performance

```bash
# Run inside WSL2 Ubuntu
# Move project to WSL2 filesystem for better performance
sudo mkdir -p /opt/neurobridge
sudo chown $USER:$USER /opt/neurobridge
cp -r /mnt/c/Users/$USER/NeuroBridge/neurobridge-edu /opt/neurobridge/

# Update volume mounts in docker-compose.yml to use WSL2 paths
# /opt/neurobridge/neurobridge-edu:/app
```

---

## 🚀 Production Deployment

### Environment Configuration

#### Production Environment Variables

```bash
# .env.production
NODE_ENV=production
LOG_LEVEL=warn

# Application URLs (update with your domain)
VITE_API_BASE_URL=https://api.neurobridge.yourdomain.com
CORS_ORIGINS=https://neurobridge.yourdomain.com,https://api.neurobridge.yourdomain.com

# Database (consider external database for production)
DATABASE_PATH=/app/data/neurobridge.db

# Security
JWT_SECRET=your-very-secure-jwt-secret-here
SECURE_COOKIES=true
HTTPS_ONLY=true

# Performance
WORKERS=4
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# Backup
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
```

### High Availability Setup

#### Load Balancer Configuration

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - backend-1
      - backend-2
    networks:
      - neurobridge-network

  backend-1:
    extends:
      file: docker-compose.yml
      service: backend
    container_name: neurobridge-backend-1
    ports: []  # Remove direct port mapping

  backend-2:
    extends:
      file: docker-compose.yml
      service: backend
    container_name: neurobridge-backend-2
    ports: []  # Remove direct port mapping

  redis:
    image: redis:alpine
    container_name: neurobridge-redis
    volumes:
      - redis-data:/data
    networks:
      - neurobridge-network

volumes:
  redis-data:
```

#### Load Balancer Nginx Configuration

```nginx
# nginx-lb.conf
upstream backend_pool {
    least_conn;
    server backend-1:3939;
    server backend-2:3939;
}

server {
    listen 80;
    listen 443 ssl;
    
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;
    
    location /api/ {
        proxy_pass http://backend_pool;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health checks
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### Database Configuration

#### External PostgreSQL Setup

```yaml
# docker-compose.postgres.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: neurobridge-postgres
    environment:
      POSTGRES_DB: neurobridge
      POSTGRES_USER: neurobridge_user
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - neurobridge-network

  backend:
    environment:
      - DATABASE_URL=postgresql://neurobridge_user:secure_password_here@postgres:5432/neurobridge
    depends_on:
      - postgres

volumes:
  postgres_data:
```

---

## 🏢 Enterprise Features

### Active Directory Integration

#### LDAP Authentication Configuration

```python
# Add to backend configuration
LDAP_CONFIG = {
    'server': 'ldap://your-ad-server.company.com',
    'base_dn': 'OU=Users,DC=company,DC=com',
    'search_filter': '(sAMAccountName={username})',
    'bind_user': 'service-account@company.com',
    'bind_password': 'service-account-password'
}
```

### Single Sign-On (SSO)

#### SAML Configuration

```yaml
# Add to docker-compose.yml
services:
  saml-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy
    container_name: neurobridge-sso
    ports:
      - "4180:4180"
    environment:
      - OAUTH2_PROXY_PROVIDER=saml
      - OAUTH2_PROXY_SAML_IDP_URL=https://your-saml-provider.com/sso
      - OAUTH2_PROXY_UPSTREAM=http://frontend:3131
    volumes:
      - ./saml-config:/etc/oauth2-proxy
```

### Enterprise Logging

#### Centralized Logging with ELK Stack

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    container_name: neurobridge-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    container_name: neurobridge-logstash
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    container_name: neurobridge-kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

---

## 💾 Backup and Recovery

### Automated Backup Solution

#### Backup Script

```powershell
# backup-neurobridge.ps1
param(
    [string]$BackupPath = "$env:USERPROFILE\NeuroBridge\backups",
    [int]$RetentionDays = 30
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupName = "neurobridge-backup-$timestamp"
$fullBackupPath = Join-Path $BackupPath $backupName

# Create backup directory
New-Item -ItemType Directory -Path $fullBackupPath -Force | Out-Null

Write-Host "🔄 Starting backup to: $fullBackupPath"

# Backup application files
Write-Host "📁 Backing up application files..."
robocopy "$env:USERPROFILE\NeuroBridge\neurobridge-edu" "$fullBackupPath\app" /E /XD node_modules .git logs __pycache__ /XF "*.log" "*.tmp"

# Backup Docker volumes
Write-Host "💾 Backing up Docker volumes..."
$volumes = docker volume ls --filter "name=neurobridge" --format "{{.Name}}"
foreach ($volume in $volumes) {
    if ($volume) {
        docker run --rm -v ${volume}:/data -v ${fullBackupPath}:/backup alpine tar czf /backup/volume-$volume.tar.gz -C /data .
    }
}

# Backup database
Write-Host "🗄️  Backing up database..."
docker compose exec -T backend python -c "
import sqlite3
import shutil
import os
db_path = os.getenv('DATABASE_PATH', '/app/data/neurobridge.db')
if os.path.exists(db_path):
    shutil.copy2(db_path, '/app/data/backup.db')
    print('Database backup created')
"
docker cp neurobridge-backend:/app/data/backup.db "$fullBackupPath\neurobridge.db"

# Create backup manifest
$manifest = @{
    timestamp = $timestamp
    version = "2.0.0"
    files = Get-ChildItem $fullBackupPath -Recurse | Select-Object Name, Length, LastWriteTime
    volumes = $volumes
}
$manifest | ConvertTo-Json -Depth 3 | Out-File "$fullBackupPath\manifest.json"

# Cleanup old backups
Write-Host "🧹 Cleaning up old backups..."
Get-ChildItem $BackupPath -Directory | Where-Object {
    $_.Name -match "neurobridge-backup-\d{8}-\d{6}" -and
    $_.CreationTime -lt (Get-Date).AddDays(-$RetentionDays)
} | Remove-Item -Recurse -Force

Write-Host "✅ Backup completed successfully!"
Write-Host "📍 Backup location: $fullBackupPath"
```

#### Restore Script

```powershell
# restore-neurobridge.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath,
    
    [switch]$Force
)

if (-not (Test-Path $BackupPath)) {
    Write-Error "Backup path not found: $BackupPath"
    exit 1
}

$manifest = Get-Content "$BackupPath\manifest.json" | ConvertFrom-Json
Write-Host "🔄 Restoring from backup: $($manifest.timestamp)"

if (-not $Force) {
    $confirm = Read-Host "This will overwrite current data. Continue? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "Restore cancelled"
        exit 0
    }
}

# Stop application
Write-Host "🛑 Stopping application..."
docker compose down

# Restore application files
Write-Host "📁 Restoring application files..."
robocopy "$BackupPath\app" "$env:USERPROFILE\NeuroBridge\neurobridge-edu" /E

# Restore Docker volumes
Write-Host "💾 Restoring Docker volumes..."
foreach ($volume in $manifest.volumes) {
    if (Test-Path "$BackupPath\volume-$volume.tar.gz") {
        docker volume create $volume
        docker run --rm -v ${volume}:/data -v ${BackupPath}:/backup alpine tar xzf /backup/volume-$volume.tar.gz -C /data
    }
}

# Restore database
Write-Host "🗄️  Restoring database..."
if (Test-Path "$BackupPath\neurobridge.db") {
    docker compose up -d backend
    docker cp "$BackupPath\neurobridge.db" neurobridge-backend:/app/data/neurobridge.db
}

# Start application
Write-Host "🚀 Starting application..."
docker compose up -d

Write-Host "✅ Restore completed successfully!"
```

### Scheduled Backups

```powershell
# Create scheduled task for daily backups
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$PWD\scripts\backup-neurobridge.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "NeuroBridge Daily Backup" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily backup of NeuroBridge EDU data"
```

---

## 📊 Monitoring and Logging

### Prometheus Metrics

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    container_name: neurobridge-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana
    container_name: neurobridge-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-dashboards:/var/lib/grafana/dashboards

  node-exporter:
    image: prom/node-exporter
    container_name: neurobridge-node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro

volumes:
  prometheus_data:
  grafana_data:
```

### Log Aggregation

```yaml
# docker-compose.logging.yml additions
services:
  fluentd:
    image: fluent/fluentd:v1.16
    container_name: neurobridge-fluentd
    volumes:
      - ./fluentd.conf:/fluentd/etc/fluent.conf
      - ./logs:/var/log/neurobridge
    depends_on:
      - elasticsearch

  backend:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: neurobridge.backend

  frontend:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: neurobridge.frontend
```

---

## 🔐 Security Hardening

### Container Security

```yaml
# docker-compose.secure.yml
version: '3.8'

services:
  backend:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    user: "1001:1001"  # Non-root user
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed for port binding

  frontend:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache/nginx
    user: "101:101"  # nginx user
```

### Firewall Configuration

```powershell
# Windows Firewall rules for NeuroBridge EDU
# Allow only necessary ports

# Remove existing rules
netsh advfirewall firewall delete rule name="NeuroBridge EDU"

# Add specific rules
netsh advfirewall firewall add rule name="NeuroBridge EDU Frontend" dir=in action=allow protocol=TCP localport=3131
netsh advfirewall firewall add rule name="NeuroBridge EDU Backend" dir=in action=allow protocol=TCP localport=3939
netsh advfirewall firewall add rule name="NeuroBridge EDU HTTPS" dir=in action=allow protocol=TCP localport=443

# Block all other inbound traffic to Docker
netsh advfirewall firewall add rule name="Block Docker Default" dir=in action=block remoteip=172.16.0.0/12
```

### Environment Secrets Management

```powershell
# Use Windows Credential Manager for secrets
# Store API keys securely

# Store OpenAI API key
cmdkey /add:neurobridge_openai /user:api /pass:sk-your-openai-api-key-here

# Retrieve in application startup script
$openaiKey = cmdkey /list:neurobridge_openai | Select-String "Target:" | ForEach-Object {
    $target = $_.ToString().Split(":")[1].Trim()
    # Retrieve the actual key using Windows API
}

# Update .env with retrieved key
(Get-Content .env) -replace 'OPENAI_API_KEY=.*', "OPENAI_API_KEY=$openaiKey" | Set-Content .env
```

---

## 📝 Configuration Templates

### Complete Production docker-compose.yml

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: neurobridge-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
      - ./www-certbot:/var/www/certbot
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
    networks:
      - neurobridge-network

  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    container_name: neurobridge-frontend
    environment:
      - NODE_ENV=production
      - VITE_API_BASE_URL=https://api.neurobridge.yourdomain.com
    volumes:
      - /app/node_modules
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3131"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - neurobridge-network

  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    container_name: neurobridge-backend
    environment:
      - HOST=0.0.0.0
      - PORT=3939
      - LOG_LEVEL=warn
      - DATABASE_URL=postgresql://user:pass@postgres:5432/neurobridge
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - CORS_ORIGINS=https://neurobridge.yourdomain.com
      - WORKERS=4
    volumes:
      - backend-data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3939/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - postgres
      - redis
    networks:
      - neurobridge-network

  postgres:
    image: postgres:15
    container_name: neurobridge-postgres
    environment:
      - POSTGRES_DB=neurobridge
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - neurobridge-network

  redis:
    image: redis:alpine
    container_name: neurobridge-redis
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - neurobridge-network

volumes:
  backend-data:
  postgres-data:
  redis-data:

networks:
  neurobridge-network:
    driver: bridge
```

### Complete .env.production Template

```bash
# Production Environment Configuration

# Application
NODE_ENV=production
LOG_LEVEL=warn
WORKERS=4

# URLs
VITE_API_BASE_URL=https://api.neurobridge.yourdomain.com
CORS_ORIGINS=https://neurobridge.yourdomain.com

# Database
DATABASE_URL=postgresql://neurobridge_user:secure_password@postgres:5432/neurobridge

# Security
JWT_SECRET=your-super-secure-jwt-secret-here
SECURE_COOKIES=true
HTTPS_ONLY=true

# AI Services
OPENAI_API_KEY=sk-your-production-openai-key

# Performance
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30
CACHE_TTL=3600

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
SENTRY_DSN=https://your-sentry-dsn-here

# Backup
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_LOCATION=/app/backups

# Email (for notifications)
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password
```

---

This advanced configuration guide provides enterprise-ready setup options for NeuroBridge EDU on Windows with Docker. Each section can be implemented independently based on your specific requirements.

For support with advanced configurations, refer to:
- [Installation Guide](installation-guide.md)
- [Troubleshooting FAQ](troubleshooting-faq.md)
- [GitHub Issues](https://github.com/your-org/neurobridge-edu/issues)

---
**NeuroBridge EDU Team** | [Documentation Home](../README.md)