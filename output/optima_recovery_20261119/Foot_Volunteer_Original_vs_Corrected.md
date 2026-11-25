# Foot_Volunteer repair report



## 1. QTM force settings and recorded data

The original QTM recordings had **Calculate Force** enabled for both the generic **Force-plate 1** and **Amti Optima OR6-7-OP-1K-STT 10409M**. The generic plate's incorrect analog channel configuration triggered the QTM warning. In the six corrected recordings and the current project settings, the generic plate is off and the Optima is on. [Project settings](../../Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Settings.qtmproj) · [Session repair record](force-plate-session-repair.json)

A byte-level comparison of the current original and corrected QTM files found one changed byte per recording in the measurement settings stream, corresponding to the generic force calculation flag changing from 1 to 0. Two project metadata streams also differed. The recorded data streams matched byte-for-byte. Offsets in the table are zero-based positions **inside** the `Measurement NBC/Data Items` stream.

| QTM file | Offset | Original | Corrected |
|---|---:|---:|---:|
| Dynamic 4 | 23,684 | 1 | 0 |
| Dynamic 5 | 23,556 | 1 | 0 |
| Dynamic 6 | 23,412 | 1 | 0 |
| Dynamic 7 | 23,276 | 1 | 0 |
| Dynamic 8 | 23,552 | 1 | 0 |
| Static 1 | 24,052 | 1 | 0 |

A separate QTM test export of Dynamic 8 completed without the generic plate warning. Its force, moments, center of pressure, plate corners, and origin matched the reference C3D. That test used an existing recording offline. Live acquisition hardware was outside this verification. [QTM re-export check](Dynamic-8-QTM-export-check.json)

## 2. C3D exports

| Trial | Original C3D | Corrected C3D | Marker frames | Corrected peak vertical force |
|---|---|---|---:|---:|
| Dynamic 4 | Readable | Byte-for-byte match | 400 | 577.66 N |
| Dynamic 5 | Readable | Byte-for-byte match | 391 | 618.12 N |
| Dynamic 6 | Readable | Byte-for-byte match | 403 | 588.50 N |
| Dynamic 7 | 4,096 bytes and unreadable | 318,976 bytes and readable, byte-for-byte match to the intact intermediate copy | 385 | 627.37 N |
| Dynamic 8 | Readable | Byte-for-byte match | 364 | 581.50 N |
| Static 1 | Readable | Byte-for-byte match | 80 | 1.93 N |

The readable C3Ds use 120 Hz marker sampling and 1,200 Hz analog sampling. The restored Dynamic 7 export has one Type 2 platform with channels 1–6 for three force and three moment components, in N and N·mm. Dynamic 7 is the only C3D that differs between these two folders. The corrected C3Ds all have zero embedded gait events.

## 3. Static calibration and the foot model

- **Session loading.** Static Analysis now accepts QTM XML with a `<Session>` inside a `<Subject>` wrapper. The measurement entries inside the original and corrected session XML match. [Static Analysis session loader](../../app/ui/pages/static_analysis_page.py)
- **Foot-model settings and marker handling.** Both foot models were enabled in the corrected session. The engine now recognizes the supported recording-specific `.Cal` label variants and passes the required metatarsal markers into the foot calculations. The corrected calibration has separate hindfoot, forefoot, and hallux transforms for each side. [Calibration calculations](../../Gait-lab-Vicon-to-QTM/static_calibration_calculations.py) · [Generated calibration](../../Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/_/Foot_Volunteer_11111/2026-11-17_1_2/Calibration/Static_BF_Foot_Volunteer.py)
- **Hindfoot angles.** The editable input file has both Hindfoot Varus/Valgus fields blank. The generated calibration inspected for this report contains **+4° left and −3° right**. Those values match the isolated demo test values. Their origin as measured angles in the generated file is unconfirmed. The existing graphs verify the workflow, and clinical interpretation depends on verifying the measurements used. [Editable inputs](../../Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/_/Foot_Volunteer_11111/2026-11-17_1_2/Static_BF_Foot_Volunteer.py) · [Generated calibration](../../Shriners_Gait_Model_PAF_v1.0/Shriners_Gait_Model_PAF_v1.0/Data/_/Foot_Volunteer_11111/2026-11-17_1_2/Calibration/Static_BF_Foot_Volunteer.py)




