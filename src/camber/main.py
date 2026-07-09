"""Camber desktop entry point.
Launches the Qt UI and starts the local API in a background thread.
"""
from __future__ import annotations
import logging
import os
import sys
import threading
from .logging_setup import setup_logging, install_excepthook, log_file
from .storage.db import init_db, default_db_path
from .extension_api.api import serve
from .ui.main_window import MainWindow

_LOG = logging.getLogger("camber")


def start_api(engine):
    def run():
        try:
            serve(engine)
        except BaseException:  # daemon thread: log the failure, don't take down the UI
            _LOG.exception("Local API failed to start "
                           "(is another Camber instance already using 127.0.0.1:8765?)")
    t = threading.Thread(target=run, daemon=True, name="camber-api")
    t.start()
    return t


def _fatal_startup_error(message: str):
    """Best-effort visible error for failures before the main window exists."""
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
        QMessageBox.critical(None, "Camber — startup error",
                             f"{message}\n\nDetails were saved to the log:\n{log_file()}")
    except Exception:
        print(f"Camber startup error: {message}", file=sys.stderr)


def main():
    logfile = setup_logging()
    # Install crash-safety hooks BEFORE any risky startup work so failures in
    # setup/init/API-thread are logged (dialog is added once the GUI exists).
    install_excepthook()
    _LOG.info("Starting Camber (log: %s)", logfile)

    db_path = default_db_path()
    _LOG.info("Database: %s", db_path)
    try:
        engine = init_db(db_path)
    except Exception:
        _LOG.exception("Failed to open database at %s (cwd=%s)", db_path, os.getcwd())
        _fatal_startup_error(f"Camber could not open its database:\n{db_path}\n\n"
                             "It may be corrupt, locked, or in a read-only folder.")
        raise
    start_api(engine)

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print("PySide6 not installed. Run: pip install PySide6")
        print("Local API still running on http://127.0.0.1:8765")
        import time
        while True:
            time.sleep(60)

    app = QApplication.instance() or QApplication(sys.argv)

    def _show_error(exc_type, exc, tb):
        if QApplication.instance() is None:
            return
        QMessageBox.critical(
            None, "Camber — unexpected error",
            f"{exc_type.__name__}: {exc}\n\n"
            "The app kept running; details were saved to the log "
            "(Help ▸ View logs folder).")

    install_excepthook(_show_error)  # upgrade: now also surfaces a dialog

    win = MainWindow(engine)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
