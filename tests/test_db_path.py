"""default_db_path() must not use a bare relative path (that breaks an installed
app whose working directory is read-only). It resolves, in order: $CAMBER_DB, an
existing ./camber.db (legacy/dev), then the per-user %LOCALAPPDATA%\\Camber dir.
"""
from __future__ import annotations

from pathlib import Path

from camber.storage.db import default_db_path, init_db


def test_env_override_wins(tmp_path, monkeypatch):
    target = tmp_path / "custom.db"
    monkeypatch.setenv("CAMBER_DB", str(target))
    assert default_db_path() == str(target)


def test_existing_cwd_db_is_preferred(tmp_path, monkeypatch):
    monkeypatch.delenv("CAMBER_DB", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "camber.db").write_bytes(b"")  # legacy DB already in the cwd
    assert Path(default_db_path()).resolve() == (tmp_path / "camber.db").resolve()


def test_falls_back_to_per_user_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("CAMBER_DB", raising=False)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)  # clean working dir, no camber.db here
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))
    monkeypatch.setenv("XDG_STATE_HOME", str(appdata))  # non-Windows fallback

    p = Path(default_db_path())
    assert p.resolve() == (appdata / "Camber" / "camber.db").resolve()
    assert p.parent.is_dir()  # created on demand

    engine = init_db(str(p))  # and it's a usable SQLite location
    engine.dispose()
    assert p.exists()
