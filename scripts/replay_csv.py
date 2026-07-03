"""Replay a sensor recording through the live ingest API.

Reads a wide/multi-channel (or tidy) CSV with camber-convert, groups it into
per-timestamp frames, maps each channel to the matching sensor of a target
asset, and POSTs the frames to Camber's ``/measurements/batch`` endpoint at a
chosen rate — so an already-recorded file plays back as if the bridge were
streaming live. This is the same path a real sensor gateway would use.

Usage (PowerShell):
    python scripts\\replay_csv.py --list                      # show assets to pick
    python scripts\\replay_csv.py RECORDING.csv --asset-id 3  # replay into asset 3
    python scripts\\replay_csv.py REC.csv --asset-id 3 --interval 0.2 --frames 500

Channels are matched to sensors by serial number (SG1, A1, ...), which is how
"Import sensor file..." names them, so replay a file into the asset you imported
it into. The app must be running (it starts the API on 127.0.0.1:8765).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

import camber_convert as bc
from camber.integrations.sensor_import import PROFILES_DIR


def _get(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=10) as r:
        return json.loads(r.read())


def _post(base: str, path: str, payload) -> None:
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30):
        pass


def iter_frames(path: str, profile=None, user_dir: str | None = None):
    """Yield (timestamp, [Measurement, ...]) — one frame per source timestamp."""
    user_dir = user_dir or PROFILES_DIR
    frame, cur = [], None
    for m in bc.stream_measurements(path, profile=profile, user_dir=user_dir):
        if cur is not None and m.timestamp != cur:
            yield cur, frame
            frame = []
        cur = m.timestamp
        frame.append(m)
    if frame:
        yield cur, frame


def replay(path: str, asset_id: int, *, host: str = "127.0.0.1", port: int = 8765,
           interval: float = 0.2, max_frames: int | None = None,
           profile=None, on_frame=None) -> int:
    base = f"http://{host}:{port}"
    sensors = _get(base, f"/assets/{asset_id}/sensors")
    serial_to_id = {s["serial_number"]: s["id"] for s in sensors}
    if not serial_to_id:
        raise SystemExit(f"asset {asset_id} has no sensors — import the file into it first.")

    sent = 0
    for i, (ts, frame) in enumerate(iter_frames(path, profile)):
        if max_frames is not None and i >= max_frames:
            break
        batch = [{"sensor_id": serial_to_id[m.sensor_id], "value": m.value,
                  "metric_type": m.metric_type, "unit": m.unit}
                 for m in frame if m.sensor_id in serial_to_id]
        if batch:
            _post(base, "/measurements/batch", batch)
            sent += len(batch)
        if on_frame:
            on_frame(i + 1, sent)
        if interval > 0:
            time.sleep(interval)
    return sent


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Replay a CSV recording through the live ingest API.")
    p.add_argument("csv", nargs="?", help="Path to the recording CSV")
    p.add_argument("--asset-id", type=int, help="Target asset id (its sensors receive the readings)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--interval", type=float, default=0.2, help="Seconds between frames (default 0.2)")
    p.add_argument("--frames", type=int, default=None, help="Max frames to replay (default: all)")
    p.add_argument("--list", action="store_true", help="List assets and exit")
    args = p.parse_args(argv)
    base = f"http://{args.host}:{args.port}"

    try:
        if args.list or not args.csv or args.asset_id is None:
            assets = _get(base, "/assets")
            print("Assets (use --asset-id):")
            for a in assets:
                print(f"  {a['id']:>3}  {a['name']}  ({a['type']})")
            if args.list:
                return 0
            print("\nProvide a CSV path and --asset-id to replay.")
            return 2
    except urllib.error.URLError as e:
        print(f"error: cannot reach Camber API at {base} — is the app running? ({e})",
              file=sys.stderr)
        return 1

    def progress(n, sent):
        print(f"\rreplayed frame {n} — {sent:,} readings sent", end="", flush=True)

    sent = replay(args.csv, args.asset_id, host=args.host, port=args.port,
                  interval=args.interval, max_frames=args.frames, on_frame=progress)
    print(f"\nDone. Sent {sent:,} readings. Watch it on the Charts tab in Live mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
