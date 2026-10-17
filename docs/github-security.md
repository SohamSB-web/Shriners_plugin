# GitHub Security & Git Collaboration Guide

## 1. Private Repository Mandate

This project must be maintained strictly as a **PRIVATE GitHub Repository**. Under no circumstances should the repository visibility be toggled to Public.

---

## 2. SSH-Based Authentication

All Git operations (cloning, fetching, pushing) must be authenticated via SSH keys rather than Personal Access Tokens embedded in URLs.

### A. Generating an Ed25519 SSH Key Pair
```bash
# Generate a modern Ed25519 SSH key
ssh-keygen -t ed25519 -C "your-email@organization.org"
```

### B. Registering the Key with SSH Agent
```bash
# Start the ssh-agent in the background
eval "$(ssh-agent -s)"   # On Linux/macOS
# On Windows PowerShell:
# Start-Service ssh-agent; ssh-add $env:USERPROFILE\.ssh\id_ed25519

# Add private key to agent
ssh-add ~/.ssh/id_ed25519
```

### C. Adding Public Key to GitHub
1. Copy the public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
2. Navigate to **GitHub → Settings → SSH and GPG keys → New SSH key**.
3. Paste the key and assign a descriptive label.
4. Verify connectivity:
   ```bash
   ssh -T git@github.com
   # Expected: "Hi username! You've successfully authenticated, but GitHub does not provide shell access."
   ```

### D. Remote URL Configuration
Ensure remotes use the SSH format rather than HTTPS with embedded credentials:
```bash
git remote set-url origin git@github.com:USERNAME/REPOSITORY.git
```
> **Security Rule**: Never embed GitHub tokens in `.git/config`, shell scripts, documentation, or commit messages.

---

## 3. Branching Strategy

The repository follows a structured Git flow:

- **`main`**: Production-ready, stable releases. Protected from direct pushes.
- **`develop`**: Primary integration branch for verified feature merges.
- **`feature/<name>`**: Feature branches branched from `develop` and merged via Pull Request.
- **`fix/<name>`**: Bug-fix branches branched from `develop` or `main`.
- **`docs/<name>`**: Documentation improvements.

---

## 4. Branch Protection Rules for `main`

To maintain stability and clinical safety, the following rules must be manually configured under **GitHub → Settings → Branches → Add branch protection rule** for `main`:

| Setting | Recommended Value | Rationale |
| :--- | :--- | :--- |
| **Require pull request before merging** | **Enabled** | Enforces peer review and traceability. |
| **Required approvals** | **At least 1-2** | Ensures two-person verification of clinical code. |
| **Dismiss stale reviews on new commits** | **Enabled** | Invalidates prior approvals if code changes. |
| **Require status checks to pass** | **Enabled** | Guarantees test suites pass before merge. |
| **Require branches to be up to date** | **Enabled** | Prevents race condition regressions. |
| **Block force pushes** | **Enabled** | Prevents history rewrites or accidental data loss. |
| **Block branch deletion** | **Enabled** | Prevents deletion of the primary release branch. |

---

## 5. Repository Security Configuration Checklist

- [ ] **Repository Visibility**: Confirmed **Private**.
- [ ] **Two-Factor Authentication (2FA)**: Required for all repository collaborators.
- [ ] **Secret Scanning**: Enabled under **Settings → Code security and analysis**.
- [ ] **Push Protection**: Enabled under **Settings → Code security and analysis**.
- [ ] **Dependabot Alerts & Security Updates**: Enabled.
- [ ] **Collaborator Access**: Follows least privilege (Write access only for active developers).
