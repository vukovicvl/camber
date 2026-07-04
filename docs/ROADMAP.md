# Camber roadmap — scale, analysis, and pilots

This document states honestly where Camber is today, where the limits are, and
the path beyond them. It exists so pilots and grant proposals can scope
realistically instead of over‑promising a production monitoring system.

## Where Camber is today (v0.1)

A working desktop platform: asset/sensor/threshold management, import of
recorded sensor data (tidy **and** wide/multi‑channel CSV, locale‑robust, via
the open MIT [`camber-convert`](https://github.com/vukovicvl/camber-convert)
library), status evaluation, dashboards, a map, time‑series charts with a
**Live** mode + ingest API, and a first **frequency‑analysis** view (FFT +
spectrogram). It ingests a real research dataset (the Vänersborg Bridge open
data) end‑to‑end. This is a credible demonstrator and a controlled‑pilot tool —
**not** a production system for continuous, unattended bridge monitoring.

## The honest limit: data scale

Camber stores measurements in **SQLite**. That is the right choice for metadata
and for **campaign / event** data (e.g. Vänersborg's 64 bridge‑opening events).
It is **not** the right choice for continuous high‑rate streams: one
30‑channel sensor at 200 Hz produces ~**520 million samples per channel per
year** (~15 billion values across the array). SQLite — and per‑point plotting —
will not scale there. We saw the early edge of this already: a single imported
recording (~1.2 M rows) needed query and rendering optimisations.

**Pilot guidance:** until the storage path below lands, scope pilots to recorded
campaigns and event windows, not 24/7 continuous acquisition.

## The path beyond it

1. **Storage** — keep SQLite for metadata and summaries; store bulk measurements
   as **Parquet in the `camber-open-shm` open format** (already produced by
   `camber-convert`). Query at scale with a columnar engine over Parquet
   (**DuckDB**) or a time‑series database (**TimescaleDB**) when a server
   deployment is wanted. Raw high‑rate data lives in Parquet; the app reads
   windows and rollups.
2. **Downsampling / rollups** — precompute decimated series and per‑window
   statistics (RMS, peak, min/max) so charts stay instant regardless of raw
   size; on‑the‑fly LTTB downsampling for arbitrary zoom. (The chart already
   does view‑clipped downsampling as a first step.)
3. **Streaming ingestion** — the `POST /measurements` ingest API is the seam. Add
   real gateway protocols (**MQTT**, OPC‑UA, vendor cloud APIs), buffering,
   gap/back‑pressure handling, and authentication for networked deployments.
4. **Analysis depth** — integrate established modal / damage‑detection libraries
   (**pyOMA2**, KOMA, …) rather than reimplement them; Camber stays the open
   *operational platform layer* above them. In‑app FFT/spectrogram is the first
   step; next are modal‑frequency tracking and environmental (temperature)
   compensation, plus strain **baseline leveling** (as the Vänersborg descriptor
   requires).
5. **Distribution** — signed Windows installer for testers (bundling the sample
   dataset + import profiles, done); optional **hosted read‑only demo** on
   synthetic/open data for outreach and grant demonstrations.

## Guardrails (unchanged)

Everything stays **open source**; no closed/paid tier or license gating. The
`camber-open-shm` format is a versioned public contract. Local‑first remains the
default — cloud is optional and additive, never a lock‑in.
