# Camber Architecture

## Layers
- **domain/** — pure entities & rules, no I/O
- **storage/** — SQLAlchemy models & SQLite engine
- **services/** — application operations (used by UI + API)
- **ui/** — PySide6 desktop windows
- **extension_api/** — local FastAPI server bound to 127.0.0.1
- **integrations/** — sensor-file adapters (wraps `camber-convert`), CSV/JSON loaders
- **mapping/**, **charts/** — visualization helpers

## Process model
The desktop app starts the local API in a background thread. External tools and
scripts can connect over HTTP at `127.0.0.1:8765` for read-only integration.

## Why a local API
It provides a clean, stable integration boundary for external tooling — no
shared imports into the app's internals, no hidden coupling.

## The open data format
Camber consumes the open `camber-open-shm` format produced by the standalone
MIT-licensed [`camber-convert`](https://github.com/vukovicvl/camber-convert)
package (a `<name>.meta.json` + `<name>.parquet` pair). The converter is kept
separate on purpose so other tools can adopt the format. See `AGENTS.md` §4 for
the format contract.
