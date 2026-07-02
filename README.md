# Camber

**Camber** is an open-source **structural health monitoring (SHM) platform for
bridges and civil infrastructure**. It is a desktop application that ingests
sensor data (vibration, displacement, strain, temperature, …), manages assets
and sensors, evaluates thresholds, and visualises status on dashboards, charts,
and a map.

Where existing open-source SHM tools are signal-processing / modal-analysis
libraries, Camber is the **operational platform layer** above them — asset
management, monitoring, and data handling — as open, vendor-neutral software.

> Camber was previously called **BridgeQ**.

## Features
- Asset & sensor management (full CRUD)
- Measurement ingestion (CSV, two-phase atomic import with an import log)
- Threshold evaluation & status
- Time-series charts (pyqtgraph)
- Map view (QtWebEngine + Leaflet)
- Local SQLite storage, multi-project database switching
- CSV / XLSX / PDF export
- Local HTTP extension API on `127.0.0.1:8765`

## Quickstart
```powershell
# Windows / PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
camber                      # launch the desktop app
python scripts\run_dev.py   # run the local API only (no Qt) on :8765
```

## The open data format & camber-convert
Camber reads an open, vendor-neutral data format produced by
[**camber-convert**](https://github.com/vukovicvl/camber-convert), a separate
MIT-licensed converter published to PyPI. Keeping the converter standalone and
MIT-licensed lets other tools adopt the open format freely.

## License

Camber is free and open-source software, licensed under the
**GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**.
See [LICENSE](LICENSE) for the full text.

In short: you are free to use, study, modify, and share Camber. If you
distribute a modified version — or run a modified version as a network service —
you must make your source code available under the same license. This keeps
Camber free for everyone.

Camber bundles the separately-developed
**[camber-convert](https://github.com/vukovicvl/camber-convert)** library, which
is licensed under the more permissive **MIT** license so that other tools can
adopt the open data format freely. See [NOTICE](NOTICE) for attribution and
third-party license details.

### Contributing

Contributions are welcome. By submitting a contribution you agree to license it
under the project's license and certify that you wrote it (or have the right to
submit it) via a **Developer Certificate of Origin (DCO)** sign-off — add
`Signed-off-by: Your Name <you@example.com>` to your commits (`git commit -s`).
