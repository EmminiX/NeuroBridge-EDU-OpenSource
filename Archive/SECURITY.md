# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

## Reporting a Vulnerability

The NeuroBridge EDU team and community take security bugs seriously. We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.

To report a security issue, please use the GitHub Security Advisory ["Report a Vulnerability"](https://github.com/EmminiX/NeuroBridge-EDU-OpenSource/security/advisories/new) tab.

The NeuroBridge EDU team will send a response indicating the next steps in handling your report. After the initial reply to your report, the security team will keep you informed of the progress towards a fix and full announcement, and may ask for additional information or guidance.

## Security Features

NeuroBridge EDU implements several security measures:

### Data Protection
- **AES-256-GCM Encryption**: API keys are encrypted using military-grade encryption
- **HKDF Key Derivation**: Secure key derivation for encryption keys  
- **Local Processing**: Audio data can be processed locally, never transmitted to external servers
- **Zero Data Collection**: No user data is collected or stored by default

### API Security
- **Rate Limiting**: Prevents abuse and DoS attacks
- **CORS Protection**: Configurable cross-origin resource sharing
- **Input Validation**: All inputs are validated and sanitized
- **Secure Headers**: Security headers are automatically applied

### Infrastructure Security
- **Docker Security**: Multi-stage builds and minimal base images
- **Environment Isolation**: Sensitive configuration via environment variables
- **Database Security**: Parameterized queries prevent SQL injection
- **File Permissions**: Secure file permissions for sensitive data

### Development Security
- **Dependency Scanning**: Automated vulnerability scanning of dependencies
- **Security Linting**: Code analysis for security vulnerabilities
- **Secrets Detection**: Prevents accidental commit of secrets
- **HTTPS Enforcement**: Production deployments require HTTPS

## Security Best Practices for Users

1. **API Keys**: Store API keys securely using the built-in encrypted storage
2. **Updates**: Keep NeuroBridge EDU updated to the latest version
3. **Network**: Use HTTPS in production environments
4. **Access Control**: Implement proper authentication and authorization
5. **Monitoring**: Monitor logs for suspicious activity

## Security Considerations for Developers

1. **Never commit secrets**: Use environment variables for sensitive data
2. **Validate inputs**: Always validate and sanitize user inputs
3. **Use HTTPS**: Ensure secure communication in production
4. **Regular audits**: Conduct regular security audits and dependency updates
5. **Follow OWASP**: Adhere to OWASP security guidelines

## Contact

For security-related questions or concerns, please contact:
- GitHub Security Advisory: [Report a Vulnerability](https://github.com/EmminiX/NeuroBridge-EDU-OpenSource/security/advisories/new)
- Email: security@neurobridge.edu (if available)