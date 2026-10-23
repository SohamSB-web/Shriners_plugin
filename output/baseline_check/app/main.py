# -*- coding: utf-8 -*-
"""
Shriners Gait Analysis Platform — Entry Point.

Run with:
    python -m app.main
    or
    python app/main.py
"""

import sys
import os

# Ensure the project root is on the path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.application import create_application, setup_logging


def main():
    """Launch the Shriners Gait Analysis Platform."""
    setup_logging()

    import logging
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("  Shriners Gait Analysis Platform — Starting")
    logger.info("=" * 60)

    app, window = create_application()
    window.show()
    app.processEvents()

    logger.info("Application window shown — entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
