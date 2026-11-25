import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.ui.pages.static_analysis_page import StaticAnalysisPage

session = Path(sys.argv[1]).resolve(strict=True)
app = QApplication([])
page = StaticAnalysisPage()
page.set_session(str(session))
assert page._filename == "Static 1.qtm", page._filename
result = []
page._service.processing_log.connect(print)
page._service.processing_finished.connect(result.append)
def check_finished():
    if result and not page._service.is_running:
        app.quit()
timer = QTimer()
timer.timeout.connect(check_finished)
timer.start(50)
QTimer.singleShot(45000, app.quit)
page._run_btn.click()
assert page._service.is_running, "The Static Analysis Run button did not start processing"
app.exec()
assert result and result[0].completed, result
assert page._progress_bar.value() == 100
print("PASS: Static Analysis Save & Run completed via the application page")
