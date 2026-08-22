"""MechaPet application entry point."""

import sys
import logging
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app.pet_window import PetWindow
from app.config import PROJECT_ROOT


def configure_logging() -> None:
    """Configure concise rotating logs without recording secrets."""
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    file_handler = RotatingFileHandler(
        PROJECT_ROOT / "mechapet.log",
        maxBytes=500_000,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[file_handler])


def main() -> int:
    """Start the desktop pet."""
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("MechaPet starting")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("MechaPet")
    app.setQuitOnLastWindowClosed(False)

    pet = PetWindow()
    pet.show()
    exit_code = app.exec()
    logger.info("MechaPet stopped with exit code %s", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
