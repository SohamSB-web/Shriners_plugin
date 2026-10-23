import os
from pathlib import Path
from Py3_varExtractor import extract_fields_by_filename
import sys

def main():
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    sess_dir = data_dir / "test_002" / "2025-02-21_0003"
    if not sess_dir.is_dir():
        sess_dir = data_dir / "Shriners_test_002" / "2025-02-21_0003"
    filepath = str(sess_dir)
    filename = "Dynamic 1.qtm"
    fields = extract_fields_by_filename(filepath, filename)
    
    print(f"Capture Frequency: {fields['Capture_Frequency']}")
    print("Events:")
    for k, v in fields['Events'].items():
        print(f"  {k}: Frames {v['FrameNo']}, Offsets {v['EventOffset']}")
        
if __name__ == '__main__':
    main()
