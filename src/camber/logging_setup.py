"""Application logging + crash-safety hooks.

Testers churn on silent crashes. This writes a rotating log to a per-user
location and installs hooks so an uncaught error — on the **main thread or a
worker thread** — is logged (and, if the UI is up, surfaced in a dialog) instead
of vanishing. Nothing here may itself raise during startup: if the log location
is unwritable it falls back to console-only. The "Report an issue" / "View logs"
Help actions point here.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG = logging.getLogger("camber")


def _intended_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_STATE_HOME") or str(Path.home())
    return Path(base) / "Camber" / "logs"


def log_dir() -> Path:
    """Per-user log directory, created on demand (used by the Help menu)."""
    d = _intended_log_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file() -> Path:
    """Intended log-file path. Never raises (does not touch the filesystem)."""
    return _intended_log_dir() / "camber.log"


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure root logging (rotating file + console). Resilient: if the file
    handler can't be created, logs to console only rather than failing startup."""
    path = log_file()
    root = logging.getLogger()
    if any(getattr(h, "_camber", False) for h in root.handlers):
        return path  # already configured
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch._camber = True  # type: ignore[attr-defined]
    root.addHandler(ch)

    try:
        _intended_log_dir().mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        fh._camber = True  # type: ignore[attr-defined]
        root.addHandler(fh)
        _LOG.info("Camber logging initialised -> %s", path)
    except OSError as e:
        _LOG.warning("File logging unavailable (%s); logging to console only.", e)
    return path


def install_excepthook(on_error=None) -> None:
    """Log uncaught exceptions on the main thread AND worker threads (optionally
    notifying via ``on_error``) instead of dying silently. Safe to call twice
    (the second call just refreshes ``on_error``)."""
    def _handle(exc_type, exc, tb, thread_name: str | None = None):
        if issubclass(exc_type, KeyboardInterrupt):
            return False
        where = f" in thread {thread_name}" if thread_name else ""
        _LOG.error("Uncaught exception%s", where, exc_info=(exc_type, exc, tb))
        if on_error is not None:
            try:
                on_error(exc_type, exc, tb)
            except Exception:
                _LOG.exception("error handler itself failed")
        return True

    def main_hook(exc_type, exc, tb):
        if not _handle(exc_type, exc, tb):
            sys.__excepthook__(exc_type, exc, tb)

    def thread_hook(args):
        # daemon/worker-thread exceptions never reach sys.excepthook — capture
        # them here (e.g. the FastAPI server thread failing to bind its port).
        name = args.thread.name if args.thread is not None else None
        _handle(args.exc_type, args.exc_value, args.exc_traceback, name)

    sys.excepthook = main_hook
    threading.excepthook = thread_hook
