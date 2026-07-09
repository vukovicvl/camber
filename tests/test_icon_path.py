"""Regression: _icon_path() must find the window icon in the frozen build.

In a PyInstaller onedir build the bundled icons sit at the _MEIPASS (_internal)
root, not three directories above the ui module, so the source-only "../../../"
walk missed them and the window/taskbar icon was silently absent. _icon_path()
now searches sys._MEIPASS first when frozen.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from camber.ui.main_window import _icon_path


def test_finds_icon_in_frozen_meipass(tmp_path, monkeypatch):
    icon = tmp_path / "camber_icon.png"
    icon.write_bytes(b"\x89PNG\r\n")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert Path(_icon_path()) == icon


def test_frozen_falls_back_to_source_when_meipass_lacks_icon(tmp_path, monkeypatch):
    # frozen, but _MEIPASS has no icon -> must fall back to the repo-root copy
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    p = _icon_path()
    assert p is not None and os.path.basename(p) in ("camber_icon.png", "camber_icon.ico")


def test_source_checkout_still_resolves(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    p = _icon_path()
    assert p is not None and os.path.exists(p)
