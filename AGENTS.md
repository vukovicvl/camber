# AGENTS.md — Camber project context for coding agents

> How to use this file: this is the project brief for an AI coding agent (Claude
> Code, Cursor, Copilot, etc.) working on Camber in VS Code. Read it fully
> before making changes. If you use Claude Code, you can rename or symlink this
> to `CLAUDE.md`. Keep this file updated as decisions change.
>
> **Naming note:** the project was previously called **BridgeQ** and was renamed
> to **Camber**. The rename is now **complete** across all three parts: the
> converter package, the license kit, and the desktop-app source (package
> `src/camber/`, `camber.spec`, `_camber_launcher.py`, `camber_icon.*`,
> `installer.iss`, `pyproject.toml`, and all imports/strings). The layout below
> matches reality. What remains is to recreate the dev venv and rebuild the
> `.exe` under the new name (see Task 0).

---

## 1. What Camber is

Camber is an open-source **structural health monitoring (SHM) platform for
bridges and civil infrastructure**. It is a desktop application that ingests
sensor data (vibration, displacement, strain, temperature, ...), manages assets
and sensors, evaluates thresholds, and visualises status on dashboards, charts,
and a map.

The market position that matters: existing open-source SHM tools (pyOMA2, KOMA,
Modalyzer, SHMTools) are **signal-processing / modal-analysis libraries**.
Camber is the **operational platform layer** above them — asset management,
monitoring, data handling — which is almost entirely proprietary/vendor-locked
today. Camber aims to be the open, vendor-neutral platform in that gap.

---

## 2. Locked decisions (do not silently change these)

These were decided deliberately. If a change seems warranted, flag it to the
maintainer rather than just doing it.

1. **Everything is free and open source.** There is **no proprietary "Pro"
   module** anymore. An earlier design had a closed Pro tier (alarms, scheduler,
   notifications, reports); that has been folded into the open application.
   Do **not** reintroduce a closed boundary, license gating, or activation logic.
2. **No QGIS plugin.** An earlier design had a companion QGIS plugin. It has
   been dropped. Do not add QGIS-specific code.
3. **Two repositories, two licenses:**
   - **`camber`** (the desktop app) → **AGPL-3.0-or-later**. Everything the app
     is made of lives here and is AGPL.
   - **`camber-convert`** (the data converter) → **MIT**, in its **own repo**
     and published to **PyPI**. It is separate on purpose: MIT + standalone
     package is what lets other tools adopt the open data format. The app
     depends on it (`pip install camber-convert`) and bundles it into the
     `.exe`.
4. **The open data format** (produced by camber-convert) is the strategic
   asset — the "GTFS of structural monitoring". Treat its schema as a public
   contract; version it (see §4) and avoid breaking changes.

---

## 3. Repository layout

### `camber` (AGPL desktop app) — already scaffolded, v0.1.0

```
camber/
├── LICENSE                      # AGPL-3.0 (full text)
├── NOTICE                       # attributes bundled MIT camber-convert
├── README.md                    # include the license section provided
├── CONTRIBUTING.md              # DCO sign-off policy (TO ADD)
├── CHANGELOG.md                 # (TO ADD)
├── pyproject.toml
├── camber.spec                 # PyInstaller
├── installer.iss                # Inno Setup
├── licenses/                    # third-party license texts for the packaged build
├── docs/
│   └── architecture.md
├── scripts/
│   ├── build_exe.py
│   ├── run_dev.py
│   └── seed_demo_data.py
├── src/camber/
│   ├── main.py
│   ├── config.py
│   ├── domain/models.py         # Asset, Sensor, Measurement, ThresholdRule, StatusSnapshot
│   ├── services/services.py     # CRUD + ImportService (CSV, two-phase validation)
│   ├── services/exports.py      # CSV / XLSX / PDF export
│   ├── storage/db.py            # SQLAlchemy 2.x + SQLite
│   ├── ui/                      # PySide6: main_window, dialogs, dashboard_panel, settings_dialog, theme
│   ├── charts/chart_panel.py    # pyqtgraph
│   ├── mapping/map_panel.py     # QtWebEngine + Leaflet (CartoDB dark tiles)
│   ├── integrations/            # ← wire camber-convert in here (currently empty)
│   └── extension_api/api.py     # FastAPI local API on 127.0.0.1:8765
└── tests/
    └── test_thresholds.py
```

### `camber-convert` (MIT converter) — scaffolded in this handoff

```
camber-convert/
├── LICENSE                      # MIT
├── README.md
├── pyproject.toml               # MIT, entry point `camber-convert`, dep: pyarrow
├── src/camber_convert/
│   ├── __init__.py              # public API: read(), convert(), write_dataset()
│   ├── model.py                 # Dataset, Asset, Sensor, Measurement, Location
│   ├── cli.py                   # `camber-convert INPUT -o OUT --name NAME`
│   ├── readers/
│   │   ├── base.py              # @register(ext) registry + read() dispatch
│   │   ├── csv_reader.py        # ✅ implemented
│   │   ├── tdms_reader.py       # 🚧 stub (plan in docstring)
│   │   └── dewesoft_reader.py   # 🚧 stub (plan in docstring)
│   └── writers/
│       ├── json_writer.py       # <name>.meta.json
│       └── parquet_writer.py     # <name>.parquet (pyarrow, no pandas)
└── tests/
    └── test_csv_roundtrip.py    # passing
```

---

## 4. The open data format (contract)

Two files per dataset. Constants live in `camber_convert/model.py`
(`FORMAT_NAME = "camber-open-shm"`, `FORMAT_VERSION = "0.1.0"`).

**`<name>.meta.json`** — metadata:
```json
{
  "format": "camber-open-shm",
  "version": "0.1.0",
  "generated_at": "<ISO-8601 UTC>",
  "asset": { "id": "...", "name": "...", "type": "bridge", "metadata": {} },
  "sensors": [
    { "id": "...", "asset_id": "...", "sensor_type": "...",
      "unit": "...", "serial_number": null, "axis": "z" }
  ],
  "measurements_file": "<name>.parquet",
  "measurement_count": 1234,
  "source": { "reader": "csv", "original_file": "..." }
}
```

**`<name>.parquet`** — tidy/long measurements:

| column | type |
| --- | --- |
| `timestamp` | `timestamp[ms, UTC]` |
| `sensor_id` | `string` |
| `metric_type` | `string` |
| `value` | `double` |
| `unit` | `string` |

Rule: bump `FORMAT_VERSION` on any breaking change; prefer additive changes.
The field names deliberately mirror Camber's `domain/models.py` so the two
line up.

---

## 5. Environment & tooling (important — non-standard)

- **OS: Windows only. Shell: PowerShell.** Not Linux/macOS. Give commands in
  PowerShell form. Use `;` not `&&` for chaining, `Remove-Item` not `rm`, etc.
- **Python 3.14.** Newer than most wheels expect. **Known risk:** some packages
  (e.g. `pyarrow`, native GUI deps) may not yet publish 3.14 wheels. If
  `pip install pyarrow` fails to find a wheel:
    - verify with `pip debug --verbose` / check PyPI for a cp314 wheel,
    - as a fallback, develop `camber-convert` in a Python 3.12 or 3.13 venv
      (the code targets `>=3.10`), or install pyarrow via conda,
    - do **not** pin the whole project to 3.14 in a way that blocks CI on other
      versions.
- **App stack:** PySide6, SQLAlchemy 2.x + SQLite, FastAPI + uvicorn (local IPC
  on `127.0.0.1:8765`), pyqtgraph, QtWebEngine + Leaflet, openpyxl, reportlab,
  Pillow.
- **Packaging:** PyInstaller (`camber.spec`, uses a bootstrap launcher pattern
  to fix relative-import issues) + Inno Setup (`installer.iss`).
- **Build gotcha:** before rebuilding the `.exe`, make sure the old one is not
  running or PyInstaller can't overwrite it:
  ```powershell
  Stop-Process -Name Camber -ErrorAction SilentlyContinue
  python scripts\build_exe.py
  ```

---

## 6. Current state

**Built and working (camber v0.1.0):** full CRUD for Assets/Sensors/Thresholds;
empty-state dashboard with "Add Bridge" CTA; atomic CSV import with two-phase
validation + import log; CSV/XLSX/PDF export; settings dialog (color picker,
multi-project DB switching) + import history; keyboard shortcuts + full menu bar;
in-app `USER_GUIDE.md` markdown viewer; dark monitoring theme; Windows `.exe` +
installer; FastAPI local API.

**Built and working (camber-convert):** CSV reader → JSON+Parquet open format;
CLI; Python API; round-trip test passing.

**Not built yet:** the TDMS and Dewesoft readers (stubs); the wiring that makes
the Camber app *use* camber-convert; CONTRIBUTING.md and CHANGELOG.md for the
app; the former "Pro" features are not present in this open build and need to be
(re)built as normal open features if still wanted.

---

## 7. Task backlog (suggested priority order)

0. **BridgeQ → Camber rename — DONE (verify build).** The source rename is
   complete (`src/camber/`, `camber.spec`, `_camber_launcher.py`, `camber_icon.*`,
   `installer.iss`, `pyproject.toml`, all imports/strings). The old app's built
   artifacts and venv were archived, not carried over. **Remaining:** recreate a
   dev venv (`python -m venv .venv; .\.venv\Scripts\pip install -e .`), run the
   app (`camber`), then rebuild the `.exe` (`python scripts\build_exe.py`) and
   confirm `dist\Camber\Camber.exe` launches.
1. **Wire the converter into the app.** In `camber/src/camber/integrations/`,
   add an adapter that calls `camber_convert.read(path)` and maps the returned
   `Dataset` (Asset/Sensor/Measurement) into Camber's SQLAlchemy models via the
   existing services. Add an "Import from sensor file..." menu action alongside
   the current "Import CSV". Add `camber-convert` to the app's dependencies.
2. **CONTRIBUTING.md + CHANGELOG.md** for the app (DCO sign-off; Keep a Changelog
   format). Needed before opening to university contributors.
3. **Implement `readers/tdms_reader.py`** per its docstring (nptdms). Add tests
   with a small synthetic `.tdms`.
4. **Decide Dewesoft path** (CSV-export vs native DWDataReaderLib) and implement.
5. **Format validation:** add a `validate()` that checks a meta.json/parquet
   pair against the FORMAT_VERSION contract; wire into CLI (`--check`).
6. **Round-trip export:** let the app (or camber-convert) *write* the open
   format from Camber's DB, not just read it — makes Camber a full producer of
   the standard.
7. **Streaming for large files** (see performance TODO in `model.py`): let
   readers yield chunks to the Parquet writer instead of materialising all
   measurements in memory.
8. Optional: a small public **demo web app** that reads the open format and shows
   a map + per-bridge status tiles, on synthetic data — for grant/marketing use.

---

## 8. Working conventions

- **Deliver complete files, not fragments.** The maintainer prefers full,
  runnable files over partial snippets or diffs-in-prose.
- **Keep `camber-convert` dependency-light.** Core depends only on `pyarrow`.
  Put anything heavier behind an optional extra (as TDMS is behind `[tdms]`).
- **Don't blur the license boundary.** New converter code → MIT repo. New app
  code → AGPL repo. If code could be reused by other tools, it probably belongs
  in camber-convert (MIT).
- **Test data:** the maintainer keeps CSV fixtures for normal, warning, critical,
  a realistic 24-hour run, and malformed data. Reuse/extend these for tests.
- **Windows/PowerShell** for all shell instructions (see §5).
- **Serbian:** the maintainer is Serbian and may want national-application docs
  in Serbian; code and code comments stay in English.

---

## 9. Guardrails (do NOT)

- Do **not** add a proprietary/paid tier, license keys, or activation logic.
- Do **not** add a QGIS plugin or QGIS dependencies.
- Do **not** move converter logic into the AGPL app repo (keep it MIT/standalone).
- Do **not** introduce cloud dependencies without a clear, discussed reason
  (the app is on-prem/local-first by design).
- Do **not** make breaking changes to the open format without bumping
  `FORMAT_VERSION` and flagging it.
- Do **not** hard-pin the project to Python 3.14 in a way that blocks other
  versions; the code targets `>=3.10`.
