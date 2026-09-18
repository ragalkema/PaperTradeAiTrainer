import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from dashboard.application.view_models import DashboardSnapshot
from dashboard.presentation.windows import MainWindow
from PySide6.QtWidgets import QApplication


@pytest.mark.unit
def test_main_window_starts_navigates_and_closes() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow(lambda: DashboardSnapshot(), DashboardSnapshot(), 60_000)
    assert window.windowTitle() == "PaperTrade AI Trainer"
    window.navigate(3)
    assert window.stack.currentIndex() == 3
    assert window.nav_buttons[3].isChecked()
    window.close()
    application.processEvents()
