# Security Policy

## 1. Reporting a Vulnerability

If you discover a security vulnerability or potential credential/data exposure in this project, **DO NOT** open a public or shared GitHub issue.

Please report the finding privately by contacting the security and engineering leads:
- **Designated Contact**: Project Administrator / Security Lead
- **Email**: `security-team@hospital-organization.placeholder` *(Replace with authorized institutional contact)*
- **Subject**: `[CONFIDENTIAL SECURITY REPORT] - Shriners Gait Analysis Platform`

Please include:
1. Detailed description of the vulnerability or data leakage concern.
2. Steps to reproduce or demonstration of the issue.
3. Potential impact on clinical operations, data confidentiality, or hospital systems.
4. Proposed remediations, if available.

Reports will be acknowledged within 48 hours, followed by a remediation timeline.

---

## 2. Supported Versions

Only the current primary branch and the latest tagged releases receive security fixes:

| Version / Branch | Supported | Notes |
| :--- | :---: | :--- |
| `main` | :white_check_mark: | Active development & stable releases |
| `develop` | :white_check_mark: | Pre-release integration |
| Legacy tags (< 1.0) | :x: | Unsupported |

---

## 3. Confidential Clinical Data Policy

- Version control must never contain identifiable patient information, medical records, or raw clinical recordings (`.qtm`, `.c3d`, `.GCD`, `.avi`).
- If patient information is accidentally pushed to Git, notify the administrative contact immediately to coordinate Git history scrubbing and incident logging under institutional governance.

---

## 4. Credential & Secret Management

- Any leaked API key, database credential, or token must be **immediately revoked and rotated**.
- Deleting the commit alone does not eliminate the compromise; credentials exposed in history must be assumed compromised until rotated.
- All secrets must be passed via secure environment variables or institutional secrets management.

---

## 5. Access Control & Authorization

- Access to this private repository is granted strictly on a need-to-know, least-privilege basis.
- Two-factor authentication (2FA) is mandatory for all contributors.
