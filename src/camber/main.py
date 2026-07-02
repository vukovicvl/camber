"""Camber desktop entry point.
Launches the Qt UI and starts the local API in a background thread.
"""
from __future__ import annotations
import sys
import threading
from .storage.db import init_db
from .extension_api.api import serve
from .ui.main_window import MainWindow


def start_api(engine):
    t = threading.Thread(target=serve, args=(engine,), daemon=True)
    t.start()
    return t


def main():
    engine = init_db("camber.db")
    start_api(engine)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 not installed. Run: pip install PySide6")
        print("Local API still running on http://127.0.0.1:8765")
        import time
        while True:
            time.sleep(60)

    app = QApplication(sys.argv)
    win = MainWindow(engine)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
