# NeuroBridge EDU - Windows Docker Documentation 🐳

Complete Windows Docker deployment documentation for NeuroBridge EDU. This documentation suite provides everything you need to install, configure, and manage NeuroBridge EDU on Windows using Docker Desktop.

## 🚀 Quick Navigation

### For New Users
- **[⚡ Quick Start Guide](quick-start-guide.md)** - Get running in 10 minutes
- **[📖 Complete Installation Guide](installation-guide.md)** - Step-by-step setup with WSL2

### For IT Professionals
- **[🔧 Troubleshooting FAQ](troubleshooting-faq.md)** - Solve Windows-specific issues
- **[⚙️ Advanced Configuration](advanced-configuration.md)** - Production setup, SSL, monitoring

### Automation & Scripts
- **[📜 PowerShell Scripts](../../scripts/windows/)** - Automated installation and management
- **[🖥️ Desktop Integration](../../scripts/windows/create-desktop-shortcuts.ps1)** - Windows shortcuts and system integration

## 📋 What's Included

### 📚 Documentation
| Guide | Description | Audience | Time |
|-------|-------------|-----------|------|
| [Quick Start Guide](quick-start-guide.md) | Fastest way to get running | All users | 10 min |
| [Installation Guide](installation-guide.md) | Complete setup instructions | All users | 30 min |
| [Troubleshooting FAQ](troubleshooting-faq.md) | Common issues and solutions | All users | Reference |
| [Advanced Configuration](advanced-configuration.md) | Enterprise features | IT Professionals | 60+ min |

### 🛠️ Automation Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `install-neurobridge.ps1` | Automated installation | `.\install-neurobridge.ps1 -OpenAIKey "sk-..."` |
| `manage-neurobridge.ps1` | Application management | `.\manage-neurobridge.ps1 start\|stop\|status` |
| `create-desktop-shortcuts.ps1` | Desktop integration | `.\create-desktop-shortcuts.ps1` |

### 🐳 Docker Configuration
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main application stack |
| `docker/Dockerfile.frontend` | React frontend container |
| `docker/Dockerfile.backend` | Python backend container |
| `.dockerignore` | Build optimization |
| `.env.example` | Configuration template |

## 🎯 Choose Your Path

### 🆕 First Time User
```
1. Quick Start Guide → 2. Desktop Integration → 3. Done! 🎉
```

### 👨‍💻 Developer
```
1. Installation Guide → 2. Advanced Configuration → 3. Troubleshooting FAQ
```

### 🏢 Enterprise IT
```
1. Installation Guide → 2. Advanced Configuration → 3. Automation Scripts → 4. Monitoring Setup
```

## 🚀 One-Command Installation

For the ultimate quick start:

```powershell
# Download and run the installer
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/your-org/neurobridge-edu/main/scripts/windows/install-neurobridge.ps1" -OutFile "install.ps1"
.\install.ps1 -OpenAIKey "sk-your-openai-api-key-here"
```

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows 10 Pro/Enterprise (1903+) or Windows 11
- **Memory**: 8 GB RAM
- **Storage**: 20 GB free space
- **CPU**: Intel/AMD with virtualization support

### Recommended
- **OS**: Windows 11 Pro (latest)
- **Memory**: 16 GB RAM
- **Storage**: 50 GB SSD space  
- **CPU**: Intel Core i5 / AMD Ryzen 5+

## 🛠️ What Gets Installed

### Core Components
- **Docker Desktop** - Container runtime for Windows
- **WSL2** - Windows Subsystem for Linux v2
- **Ubuntu** - WSL2 Linux distribution
- **NeuroBridge EDU** - The application stack

### Application Services
- **Frontend** (Port 3131) - React web interface
- **Backend** (Port 3939) - Python FastAPI server
- **Database** - SQLite for data persistence

### Windows Integration
- **Desktop Shortcuts** - One-click access
- **Start Menu Entries** - Management commands  
- **System Tray** - Quick status checks
- **Firewall Rules** - Secure network access

## 🔧 Management Commands

After installation, manage your application with:

```powershell
# Application lifecycle
.\manage-neurobridge.ps1 start     # Start services
.\manage-neurobridge.ps1 stop      # Stop services  
.\manage-neurobridge.ps1 restart   # Restart services

# Monitoring & maintenance
.\manage-neurobridge.ps1 status    # Show status
.\manage-neurobridge.ps1 logs      # View logs
.\manage-neurobridge.ps1 health    # Health check

# Updates & backups
.\manage-neurobridge.ps1 update    # Update to latest
.\manage-neurobridge.ps1 backup    # Create backup
.\manage-neurobridge.ps1 reset     # Factory reset
```

## 🌐 Access URLs

Once running, access your application at:

- **🖥️ Main Application**: http://localhost:3131
- **🔧 API Backend**: http://localhost:3939  
- **📚 API Documentation**: http://localhost:3939/docs

## 🔍 Quick Troubleshooting

### Application Won't Start
```powershell
# Check Docker Desktop status
docker --version

# Restart Docker Desktop
taskkill /f /im "Docker Desktop.exe"
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Check application status
.\manage-neurobridge.ps1 status
```

### Port Already in Use
```powershell
# Find what's using the port
netstat -ano | findstr ":3131"
netstat -ano | findstr ":3939"

# Kill the process (replace PID)
taskkill /PID [PID_NUMBER] /F
```

### WSL2 Issues
```powershell
# Update WSL2
wsl --update
wsl --shutdown

# Restart Docker Desktop
```

**👉 For complete troubleshooting, see [Troubleshooting FAQ](troubleshooting-faq.md)**

## 📊 Performance Tips

### Optimize Docker Desktop
1. **Increase Memory**: Settings → Resources → 8GB+ RAM
2. **More CPUs**: Settings → Resources → 4+ cores  
3. **WSL2 Backend**: Settings → General → Use WSL2

### Optimize Windows
1. **Defender Exclusions**: Exclude Docker and project folders
2. **WSL2 Resources**: Configure `.wslconfig` file
3. **SSD Storage**: Use SSD for Docker images and data

### Project Location
- **Best**: WSL2 filesystem (`/home/user/project`)
- **Good**: Windows SSD (`C:\Users\Name\NeuroBridge`)
- **Avoid**: Network drives or slow HDDs

## 🔒 Security Considerations

### Development Environment
- Application runs on `localhost` only
- Uses self-signed certificates  
- Windows Firewall rules for local access

### Production Environment  
- SSL/TLS certificates required
- External database recommended
- Reverse proxy configuration
- Regular security updates

**👉 For production setup, see [Advanced Configuration](advanced-configuration.md)**

## 📚 Additional Resources

### Official Documentation
- [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/)
- [WSL2 Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [PowerShell Documentation](https://docs.microsoft.com/en-us/powershell/)

### NeuroBridge EDU Resources
- [Main Project README](../../README.md)
- [Development Guide](../../CLAUDE.md)
- [GitHub Issues](https://github.com/your-org/neurobridge-edu/issues)

### Community & Support
- [GitHub Discussions](https://github.com/your-org/neurobridge-edu/discussions)
- [Technical Support](mailto:support@neurobridge.edu)
- [Documentation Feedback](mailto:docs@neurobridge.edu)

## 🤝 Contributing

### Documentation Improvements
1. Fork the repository
2. Edit documentation files
3. Test instructions on clean Windows system
4. Submit pull request with improvements

### Reporting Issues
- Use [GitHub Issues](https://github.com/your-org/neurobridge-edu/issues)
- Include system information and error logs
- Follow the issue template for faster resolution

## 📄 License

This documentation is part of NeuroBridge EDU, released under the MIT License. See [LICENSE](../../LICENSE) for details.

---

## 🎉 Success Checklist

After completing the setup:

- [ ] Docker Desktop installed and running
- [ ] WSL2 configured with Ubuntu  
- [ ] NeuroBridge EDU accessible at http://localhost:3131
- [ ] Microphone access working in browser
- [ ] AI summarization working with OpenAI API key
- [ ] Desktop shortcuts created
- [ ] Management commands working

**🎊 Congratulations! You've successfully deployed NeuroBridge EDU on Windows!**

---

**Questions?** Check the [Troubleshooting FAQ](troubleshooting-faq.md) or [open an issue](https://github.com/your-org/neurobridge-edu/issues).

**NeuroBridge EDU Team** | [Documentation Home](../README.md) | [Main Project](../../README.md)