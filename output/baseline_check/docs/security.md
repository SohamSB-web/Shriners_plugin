# Security Policy & Secret Management

## 1. Overview

The **Shriners Gait Analysis Platform** is designed for deployment in healthcare and clinical biomechanics environments. Protecting institutional assets, patient confidentiality, and computational integrity requires strict enforcement of software supply-chain hygiene and credential controls.

---

## 2. Secret Scanning Strategy

### A. GitHub Secret Scanning & Push Protection (Recommended Native Approach)
Since the repository is hosted as a **Private GitHub Repository**, GitHub's native security features provide enterprise-grade defense without adding external dependency overhead:
1. **GitHub Push Protection**: Blocks any developer `git push` attempt containing known secret token formats (API keys, private keys, authentication tokens).
2. **GitHub Secret Scanning**: Continuously inspects commit history and pull requests for leaked credentials across all branches.

### B. Local Pre-Commit Secret Scanning (Defense in Depth)
Developers can run **Gitleaks** locally to prevent secrets from being committed prior to pushing:
```bash
# Run standalone Gitleaks scan locally
gitleaks detect --source . --verbose
```
Alternatively, add a pre-commit hook using `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
```

---

## 3. Environment & Configuration Security

1. **Zero Hardcoded Secrets**: Passwords, tokens, database connection strings, and certificates must NEVER be written into source files.
2. **Environment Variable Injection**: All configurable credentials must be loaded via environment variables using `os.environ.get("KEY")`.
3. **Template-Only Commits**: Only `.env.example` is committed to version control. Actual `.env` files are ignored via `.gitignore`.
4. **Log Redaction**: Passwords, session tokens, and patient identifiers must never be printed to stdout, stderr, or log files. Debug logging must use placeholder strings.

---

## 4. Cryptographic Asset Standards

- **Private Keys & Certificates**: Private keys (`*.pem`, `*.key`, `*.p12`, `*.pfx`) must remain in institutional key stores or hardware security modules (HSM) and are ignored by `.gitignore`.
- **Encryption at Rest**: Any local clinical storage containing identifiable information should utilize full-disk encryption (BitLocker / LUKS) or application-layer AES-256-GCM.
- **Transport Security**: Network bridges transmitting sensor data across physical hosts must enforce TLS 1.3 or run within isolated clinical VLANs.

---

## 5. Dependency & Supply Chain Integrity

1. **Automated Vulnerability Alerts**: Enable GitHub Dependabot alerts on the private repository.
2. **Scheduled Dependency Auditing**: Regularly run vulnerability audits in the Python virtual environment:
   ```bash
   pip install pip-audit
   pip-audit
   ```
3. **Pinned Dependencies**: Production builds should pin direct and transitive dependencies with cryptographic hashes where applicable.
