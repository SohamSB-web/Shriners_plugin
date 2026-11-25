import sys
from pathlib import Path
import re
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, Qt

app = QApplication(sys.argv)
icons_dir = Path("resources/icons")
for svg_file in icons_dir.glob("*.svg"):
    raw = svg_file.read_text(encoding="utf-8")
    recolored = re.sub(r'stroke="[^"]*"', 'stroke="#FFFFFF"', raw)
    recolored = re.sub(r'fill="(?!none)[^"]*"', 'fill="#FFFFFF"', recolored)
    renderer = QSvgRenderer(QByteArray(recolored.encode("utf-8")))
    if not renderer.isValid():
        print(f"ERROR: {svg_file.name} renderer invalid")
        sys.exit(1)
    pix = QPixmap(36, 36)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    pix.setDevicePixelRatio(2.0)
    print(f"OK: {svg_file.name} -> rendered successfully")
print("All 10 SVGs rendered without error!")
