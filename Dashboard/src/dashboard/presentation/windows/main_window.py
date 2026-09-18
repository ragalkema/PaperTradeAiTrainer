"""Responsive application shell with non-blocking data refresh."""

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from dashboard.application.view_models import DashboardSnapshot
from dashboard.presentation.pages import DashboardPages

logger = logging.getLogger(__name__)


class RefreshSignals(QObject):
    completed = Signal(object)


class RefreshTask(QRunnable):
    def __init__(self, refresh: Callable[[], DashboardSnapshot]) -> None:
        super().__init__()
        self._refresh = refresh
        self.signals = RefreshSignals()

    @Slot()
    def run(self) -> None:
        self.signals.completed.emit(self._refresh())


class MainWindow(QMainWindow):
    def __init__(
        self,
        refresh: Callable[[], DashboardSnapshot],
        initial: DashboardSnapshot,
        refresh_interval_ms: int = 15_000,
    ) -> None:
        super().__init__()
        self.setWindowTitle("PaperTrade AI Trainer")
        self.setMinimumSize(1060, 700)
        self.resize(1440, 900)
        self._refresh = refresh
        self._refreshing = False
        self._pool = QThreadPool.globalInstance()
        self.pages = DashboardPages()
        self._build_shell()
        self._apply_snapshot(initial)
        self._timer = QTimer(self)
        self._timer.setInterval(refresh_interval_ms)
        self._timer.timeout.connect(self.refresh_data)
        self._timer.start()
        QTimer.singleShot(100, self.refresh_data)

    def _build_shell(self) -> None:
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 18)
        brand = QLabel("PAPERTRADE\nAI TRAINER")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(24)

        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []
        for index, (name, page) in enumerate(self.pages.items):
            button = QPushButton(name)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, position=index: self.navigate(position))
            sidebar_layout.addWidget(button)
            self.nav_buttons.append(button)
            self.stack.addWidget(page)
        sidebar_layout.addStretch()
        safety = QLabel("PAPER MODE")
        safety.setObjectName("paperBadge")
        sidebar_layout.addWidget(safety)
        outer.addWidget(sidebar)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 10, 20, 10)
        self.connection = QLabel("● CONNECTING")
        self.connection.setObjectName("muted")
        self.last_update = QLabel("Waiting for first update")
        self.last_update.setObjectName("muted")
        topbar_layout.addStretch()
        topbar_layout.addWidget(self.connection)
        topbar_layout.addSpacing(18)
        topbar_layout.addWidget(self.last_update)
        content.addWidget(topbar)
        self.error = QLabel()
        self.error.setObjectName("statusError")
        self.error.setVisible(False)
        content.addWidget(self.error)
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)
        self.setCentralWidget(root)
        self.navigate(0)

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)

    @Slot()
    def refresh_data(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        task = RefreshTask(self._refresh)
        task.signals.completed.connect(self._refresh_complete)
        self._pool.start(task)

    @Slot(object)
    def _refresh_complete(self, snapshot: object) -> None:
        self._refreshing = False
        if isinstance(snapshot, DashboardSnapshot):
            self._apply_snapshot(snapshot)

    def _apply_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.pages.update_snapshot(snapshot)
        state = snapshot.connections.get("Bitvavo")
        self.connection.setText(f"● {state or 'Not connected'}".upper())
        timestamps = [market.timestamp for market in snapshot.markets if market.timestamp]
        self.last_update.setText(
            f"Updated {max(timestamps):%H:%M:%S}" if timestamps else "Waiting for market data"
        )
        self.error.setText(" · ".join(snapshot.errors))
        self.error.setVisible(bool(snapshot.errors))

    def closeEvent(self, event: object) -> None:
        logger.info("dashboard_shutdown")
        self._timer.stop()
        self._pool.waitForDone(5000)
        super().closeEvent(event)  # type: ignore[arg-type]
