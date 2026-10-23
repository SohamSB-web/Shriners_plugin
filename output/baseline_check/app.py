# -*- coding: utf-8 -*-
"""
Shriners Gait Analysis Platform — Root Application Entry Point.

Launch the clinical desktop application with:
    python app.py
    or
    python -m app.main
"""

import os
import sys

# Ensure repository root is on sys.path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Register Conda Library/bin on Windows for DLL loading (MKL / LAPACK / PySide6)
if sys.platform == "win32":
    _lib_bin = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(_lib_bin):
        if _lib_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _lib_bin + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(_lib_bin)
            except Exception:
                pass

from app.main import main

if __name__ == "__main__":
    main()
