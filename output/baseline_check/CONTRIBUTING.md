# Contributing Guidelines

Thank you for contributing to the **Shriners Gait Analysis Platform**. As a confidential hospital-grade application, all contributions must adhere to rigorous code quality, security hygiene, and patient privacy standards.

---

## 1. Code of Conduct & Confidentiality

- **Confidentiality**: All source code, algorithmic methods, and internal documentation are proprietary. Do not distribute or discuss project components outside authorized channels.
- **Patient Privacy**: Never include real clinical files, patient names, dates of birth, or motion capture recordings in pull requests, comments, or issues.

---

## 2. Branch Naming Standards

Create feature branches off `develop`:

| Branch Pattern | Purpose | Example |
| :--- | :--- | :--- |
| `feature/<name>` | New features or UI components | `feature/auto-event-filter` |
| `fix/<name>` | Bug fixes or issue resolutions | `fix/force-plate-offset` |
| `refactor/<name>` | Code refactoring without behavior change | `refactor/qtm-grpc-service` |
| `docs/<name>` | Documentation updates | `docs/architecture-diagrams` |
| `test/<name>` | New unit or integration tests | `test/c3d-parser-fixtures` |

---

## 3. Commit Message Guidelines

Use the **Conventional Commits** specification:

```text
<type>(<scope>): <short description>

[optional longer body]
```

### Common Types:
- `feat`: A new user-facing feature or algorithmic capability.
- `fix`: A bug fix.
- `docs`: Documentation changes only.
- `style`: Formatting changes that do not affect code logic.
- `refactor`: Code reorganization that neither fixes a bug nor adds a feature.
- `test`: Adding or correcting tests.
- `chore`: Maintenance tasks, configuration updates, or dependency bumps.

---

## 4. Pull Request & Review Process

1. **Self-Review**: Run local tests and verify `.gitignore` excludes any local test runs before pushing.
2. **Secret Check**: Ensure no API keys, credentials, or `.env` files are staged.
3. **PR Description**: Provide a concise summary of changes, motivation, and validation steps.
4. **Peer Review**: At least one peer review approval is required before merging into `develop` or `main`.
5. **No Direct Pushes**: Direct pushes to `main` and `develop` are strictly prohibited.

---

## 5. Running Verification Tests Locally

Ensure the test suite passes before opening a Pull Request:

```bash
# Run unit and integration tests
pytest tests/ -v

# Or run component tests directly:
python -m unittest discover tests/
```
