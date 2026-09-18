"""Desktop composition root."""

import logging
import sys
from pathlib import Path

from data_collector.infrastructure.persistence import SqlAlchemyNewsRepository
from data_collector.infrastructure.persistence.session import data_collector_session_factory
from paper_trading.infrastructure.persistence import SqlAlchemyResearchRepository
from paper_trading.infrastructure.persistence.session import async_session_factory
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from dashboard.infrastructure.paper_trading import LiveDashboardRepository
from dashboard.presentation.themes import DARK_STYLESHEET
from dashboard.presentation.windows import MainWindow


def configure_logging() -> None:
    log_directory = Path.home() / ".papertradeaitrainer" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_directory / "dashboard.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def create_window() -> MainWindow:
    research = SqlAlchemyResearchRepository(async_session_factory)
    news = SqlAlchemyNewsRepository(data_collector_session_factory)
    repository = LiveDashboardRepository(research=research, news=news)
    return MainWindow(repository.refresh, repository.snapshot())


def main() -> int:
    configure_logging()
    logging.getLogger(__name__).info("dashboard_startup mode=paper")
    application = QApplication(sys.argv)
    application.setApplicationName("PaperTrade AI Trainer")
    application.setOrganizationName("PaperTradeAiTrainer")
    application.setStyle("Fusion")
    application.setStyleSheet(DARK_STYLESHEET)
    icon_path = Path(__file__).parents[2] / "assets" / "icons" / "app.ico"
    if icon_path.exists():
        application.setWindowIcon(QIcon(str(icon_path)))
    window = create_window()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
