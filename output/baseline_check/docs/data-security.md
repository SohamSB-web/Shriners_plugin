# Patient Data Safety & Clinical Privacy Policy

## 1. Core Principle: Git is for Source Code, Never Patient Records

The **Shriners Gait Analysis Platform** operates in medical and research settings where Protected Health Information (PHI) and clinical biomechanics datasets are handled.

> **CRITICAL DIRECTIVE**: Version control (Git/GitHub) must ONLY contain application source code, build scripts, tests, and documentation. Real patient records, identifiable recordings, and clinical session files must **NEVER** be committed under any circumstance.

---

## 2. Protected Data Classifications

The following categories of data are classified as strictly confidential and must remain outside the Git repository:

1. **Patient Identifiers**: Patient names, medical record numbers (MRNs), dates of birth (DOBs), addresses, and institutional subject identifiers.
2. **Clinical Motion Capture Files**: Raw `.qtm` trials, `.c3d` coordinate files, and `.GCD` clinical data containing patient metrics.
3. **Medical Video & Photography**: Clinical video recordings (`.avi`, `.mp4`, `.mov`) capturing patient facial features, gait cycles, or physical anatomy.
4. **Clinical Reports & Case Files**: Generated PDF clinical reports, kinematic graphs bearing patient names, and doctor consultation notes.
5. **Session Dumps & Internal Logs**: PAF session caches, `variables*.json` dumps, and `Messages/*.log` runtime traces.

---

## 3. Storage Segregation Architecture

All patient and clinical data must reside in external, secured storage directories that are isolated from version control:

```text
[ Git Repository Root ]  (Committed to GitHub)
  ├── app/
  ├── Gait-lab-Vicon-to-QTM/
  ├── docs/
  └── .gitignore  ───► BLOCKS ALL: Data/, *.qtm, *.c3d, *.GCD, *.avi

[ Isolated Clinical Data Storage ]  (Local Disk / Hospital SAN / NAS)
  └── /SecureStorage/Data/
      ├── Patient_A_MRN/
      │   ├── 2026-01-15_Session/
      │   │   ├── Dynamic 1.qtm
      │   │   ├── Dynamic 1.c3d
      │   │   └── Video.avi
```

- Storage location is specified at runtime via the `PATIENTS_DATA_LOCATION` environment variable or the **Settings** page within the application UI.
- The default local folder `Data/` is strictly ignored in `.gitignore`.

---

## 4. Development & Testing: Synthetic / Mock Fixtures

To ensure continuous integration and developer onboarding without compromising patient confidentiality:
- Unit and integration tests must utilize **de-identified, synthetically generated mock datasets** or anonymized calibration trials.
- Never use clinical patient recordings as unit test fixtures committed to Git.
- When capturing screenshots for documentation, verify that all patient names and MRNs are replaced with generic demo labels (e.g., `Patient_Demo_001`).

---

## 5. Logging & Debugging Hygiene

1. **No PHI in Standard Output**: Diagnostic loggers must not print patient names, MRNs, or raw patient file paths to standard streams.
2. **Crash Dump Sanitization**: Any crash logs sent to issue trackers must be audited to ensure medical file paths and subject parameters are scrubbed.

---

## 6. Regulatory & Compliance Notice

> **Regulatory Notice**: The software features a security-conscious architecture; formal regulatory compliance (e.g., HIPAA, GDPR, HITECH, FDA 21 CFR Part 11) requires comprehensive organizational, legal, infrastructure, and operational assessment by the deploying healthcare institution.
