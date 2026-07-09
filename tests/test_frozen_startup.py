"""Regression for the windowed (console=False) PyInstaller build, where
sys.stdout/stderr are None. uvicorn's default colour log formatter calls
sys.stdout.isatty() at construction and crashes, killing the API thread so Live
mode / ingest silently break. Camber guards the streams (_ensure_std_streams)
and runs uvicorn with log_config=None. Only surfaces in the packaged exe, so
these tests simulate the None-stream condition directly.
"""
from __future__ import annotations

import sys


def test_ensure_std_streams_replaces_none():
    from camber.main import _ensure_std_streams
    saved = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        _ensure_std_streams()
        # The bug was None.isatty(); after the guard the streams exist and
        # isatty() is callable (its value — True on Windows' NUL — doesn't matter).
        ok = (sys.stdout is not None and sys.stderr is not None
              and isinstance(sys.stdout.isatty(), bool)
              and isinstance(sys.stderr.isatty(), bool))
    finally:
        sys.stdout, sys.stderr = saved
    assert ok


def test_uvicorn_config_survives_none_stdout():
    import uvicorn.config as cfg
    saved = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        default_crashed = False
        try:
            cfg.Config(app="x:y", log_config=cfg.LOGGING_CONFIG)  # uvicorn default
        except Exception:
            default_crashed = True
        cfg.Config(app="x:y", log_config=None)  # the config Camber uses — must not crash
    finally:
        sys.stdout, sys.stderr = saved
    assert default_crashed, "expected uvicorn's default log_config to fail on None stdout"
