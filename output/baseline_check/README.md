# Gait Analysis Platform — Clinical Motion Analysis Workstation

[![Security Policy](https://img.shields.io/badge/Security-Strict%20Clinical%20Governance-teal)](#confidentiality--security-notice)
[![Repository Visibility](https://img.shields.io/badge/Visibility-Private-critical)](#confidentiality--security-notice)
[![Interface](https://img.shields.io/badge/UI-PySide6%20Qt-blue)](#system-architecture)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-success)](#installation--setup)

A hospital-grade clinical gait analysis and biomechanical motion visualization suite developed for Motion Analysis Centers (MAC). The platform automates data acquisition, auto-event labeling, kinematic/kinetic processing, and longitudinal case presentation reports across Qualisys Track Manager (QTM) and Vicon optical motion capture systems.

---

## Confidentiality & Security Notice

> **RESTRICTED ACCESS — CONFIDENTIAL HOSPITAL-GRADE APPLICATION**
>
> This repository is maintained as a **STRICTLY PRIVATE** repository. It contains proprietary biomechanical algorithms, clinical presentation software, and hospital workflow configurations.
>
> - **Patient Privacy**: Protected Health Information (PHI), patient records, medical videos, and raw clinical trials (`.qtm`, `.c3d`, `.GCD`, `.avi`) must **NEVER** be committed to version control.
> - **Security Governance**: All development must adhere to the policies documented in [docs/data-security.md](docs/data-security.md) and [docs/security.md](docs/security.md).
> - **Regulatory Disclaimer**: The platform features a security-conscious architecture; formal regulatory compliance (e.g., HIPAA, GDPR) requires institutional operational verification.

---

## Key Features

- **Modern PySide6 Workstation UI**: Clean, ergonomic medical desktop interface with responsive layout, Dark/Light theme switching, and real-time system monitors.
- **Automated Gait Event Labeling**: Accurate Foot Strike (FS) and Foot Off (FO) gait cycle detection using ground reaction forces and marker trajectories.
- **Force Plate Configuration**: Interactive 3D platform assignment, threshold tuning, and ground reaction force alignment.
- **Biomechanical Processing**: Seamless conversion of Vicon Nexus models to Qualisys, generating Gait Clinical Data (GCD) files with kinematics, kinetics, and EMG amplification.
- **Longitudinal Case Presentation (MAC_CasePresentation)**: Multi-session overlay visualization comparing pre- and post-intervention studies with automated clinical PDF reports.
- **Real-Time QTM Bridge**: Asynchronous telemetry streaming and camera control over QTM RT Protocol and gRPC.

---

## System Architecture

```text
[ Desktop Workstation UI (PySide6) ]
  ├── Dashboard & Patient Management
  ├── Static Calibration & Anthropometrics
  ├── Dynamic Trial Processing & Auto-Event Labeling
  ├── Force Plate Assignment & Thresholds
  └── MAC Case Presentation & PDF Reporting
              │
              ▼
[ Asynchronous Service Layer ]
  ├── GaitProcessingService (Background QThread Worker)
  ├── QTMBridgeService (Asyncio RT Protocol & gRPC)
  ├── EventDetectionService (Kinematic & Kinetic Event Engine)
  └── C3DService (Binary Marker & Analog Parser)
              │
              ▼
[ Biomechanical Computation Engines ]
  ├── Gait-lab-Vicon-to-QTM (Kinematics, Kinetics, EMG)
  ├── PAF Project Templates & AIM Models (Shriners_Model.qam)
  └── auto_event_trigger (Gait Cycle Segmentation)
              │
              ▼
[ Isolated Clinical Storage — OUTSIDE GIT ]
  └── /Data/ (Patient Trials: .qtm, .c3d, .GCD, .avi, Reports)
```

For complete technical specifications, see [docs/architecture.md](docs/architecture.md).

---

## Project Structure

```text
Shriners_Plugin/
│
├── app/                              # Core modern PySide6 desktop workstation
│   ├── config/                       # Settings, design tokens, and theme system
│   ├── services/                     # Asynchronous services (Gait, QTM, C3D, Events)
│   └── ui/                           # Windows, pages, dialogs, and components
│
├── Gait-lab-Vicon-to-QTM/            # Biomechanical kinematic/kinetic computation engine
│   ├── proto/                        # Protocol buffer definitions
│   ├── QTM_GRPC/                     # Embedded gRPC bridge bindings
│   └── Py3_DynamicMain.py            # Primary dynamic gait pipeline
│
├── MAC_CasePresentation/             # Clinical case reporting and comparison tool
│   ├── MAC_CasePresentation.py       # Longitudinal visualization application
│   └── *.py                          # Display and plotting configuration
│
├── QTM-GRPC/                         # Standalone QTM gRPC integration scripts
│
├── Shriners_Gait_Model_PAF_v1.0/     # Qualisys PAF project models & AIM models
│
├── tests/                            # Comprehensive component & regression tests
│
├── docs/                             # Engineering, security, and governance docs
│   ├── architecture.md               # Detailed system architecture
│   ├── security.md                   # Secret scanning and security controls
│   ├── data-security.md              # Patient privacy & clinical data segregation
│   └── github-security.md            # SSH configuration & GitHub protection rules
│
├── .env.example                      # Safe environment variable template
├── .gitattributes                    # Line ending normalization & binary rules
├── .gitignore                        # Comprehensive exclusions for clinical data & secrets
├── CONTRIBUTING.md                   # Developer workflow & commit standards
├── SECURITY.md                       # Vulnerability reporting procedure
└── README.md                         # Project documentation
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10 or 3.11 (Recommended: Conda environment `python-example`)
- Qualisys Track Manager (QTM) with real-time protocol enabled (for live capture)

### 2. Conda Environment
```bash
# Activate existing workstation environment
conda activate python-example

# Or create a new environment:
conda create -n gait-analysis python=3.10 -y
conda activate gait-analysis
& "C:\Program Files\Qualisys\Qualisys Track Manager\python.exe" -m pip install grpcio protobuf   grpcio-tools
pip install PySide6 numpy scipy matplotlib reportlab pyc3d protobuf grpcio
```

### 3. Environment Configuration
Copy the template configuration file:
```bash
cp .env.example .env
```
Edit `.env` to configure your local QTM port, hardware parameters, and clinical data path (`PATIENTS_DATA_LOCATION`).

---

## Running the Application

### Launching the Modern Clinical Workstation:
```bash
python -m app.main
```

### Launching MAC Case Presentation:
```bash
python MAC_CasePresentation/MAC_CasePresentation.py
```

### Launching Biomechanical Processing Engine Directly:
```bash
python Gait-lab-Vicon-to-QTM/GUI.py
```

---

## Testing & Quality Assurance

Run the comprehensive automated test suite:
```bash
# Run all tests using Conda Python
pytest tests/ -v

# Or run individual component test suites:
python -m unittest tests/test_all_components.py
python -m unittest tests/test_theme_toggle.py
python -m unittest tests/test_patients_data_location.py
```

---

## Security & Governance Documentation

- **[docs/security.md](docs/security.md)**: Secret scanning, push protection, and credential avoidance.
- **[docs/data-security.md](docs/data-security.md)**: Protected Health Information (PHI) segregation and clinical data policies.
- **[docs/github-security.md](docs/github-security.md)**: SSH setup, branch protection, and access control.
- **[SECURITY.md](SECURITY.md)**: Responsible vulnerability disclosure.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Git branch naming, PR reviews, and coding standards.

---

## Authors & Acknowledgments

- **Shriners Hospitals for Children**: Motion Analysis Centers network (Montreal, Philadelphia, Chicago, Lexington, Greenville, Salt Lake City).
- **Core Contributors**: Motion Analysis Center clinical engineers, biomechanists, and software teams.
