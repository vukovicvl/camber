"""Frequency-domain analysis panel — FFT magnitude spectrum + spectrogram.

Structural-health monitoring lives in the frequency domain: vibration data is
read as modal frequencies and their changes over time, not as raw wiggles. This
panel turns a sensor's stored time series into (a) an amplitude spectrum and
(b) a spectrogram, so a tester sees recognisable SHM output rather than only a
line chart. The sampling rate is estimated from the timestamps, so it works for
any recording without being told the rate.

Uses numpy only (no scipy): the short-time Fourier transform is done with
windowed numpy.fft over overlapping segments.
"""
from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
)
from sqlalchemy import select
from ..storage.db import session, SensorRow, MeasurementRow
from ..ui.theme import COLORS

MAX_SAMPLES = 131072   # cap the analysed window so a huge recording stays fast
MIN_SAMPLES = 64       # below this the spectrum is meaningless


class AnalysisPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("FREQUENCY ANALYSIS")
        title.setObjectName("labelHeader")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel("Sensor:"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.setMinimumWidth(250)
        self.sensor_combo.currentIndexChanged.connect(self.analyse)
        top.addWidget(self.sensor_combo)
        btn = QPushButton("Analyse")
        btn.clicked.connect(self.analyse)
        top.addWidget(btn)
        layout.addLayout(top)

        self.info = QLabel("")
        self.info.setObjectName("labelMuted")
        layout.addWidget(self.info)

        pg.setConfigOptions(antialias=True,
                            background=COLORS["bg_primary"],
                            foreground=COLORS["text_secondary"])

        self.fft_plot = pg.PlotWidget()
        self.fft_plot.showGrid(x=True, y=True, alpha=0.15)
        self.fft_plot.setLabel("bottom", "Frequency", units="Hz")
        self.fft_plot.setLabel("left", "Amplitude")
        self.fft_plot.setClipToView(True)
        layout.addWidget(self.fft_plot, 1)

        self.spec_plot = pg.PlotWidget()
        self.spec_plot.setLabel("bottom", "Time", units="s")
        self.spec_plot.setLabel("left", "Frequency", units="Hz")
        self.spec_img = pg.ImageItem()
        self.spec_plot.addItem(self.spec_img)
        try:
            lut = pg.colormap.get("inferno").getLookupTable(0.0, 1.0, 256)
            self.spec_img.setLookupTable(lut)
        except Exception:
            pass  # colormap is cosmetic; grayscale still works
        layout.addWidget(self.spec_plot, 1)

        self.reload_sensors()

    # ------------------------------------------------------------------ #
    def reload_sensors(self):
        current = self.sensor_combo.currentData()
        self.sensor_combo.blockSignals(True)
        self.sensor_combo.clear()
        with session(self.engine) as s:
            for r in s.execute(select(SensorRow).order_by(SensorRow.id)).scalars().all():
                self.sensor_combo.addItem(f"#{r.id}  {r.sensor_type}  ({r.serial_number})", r.id)
        if current is not None:
            idx = self.sensor_combo.findData(current)
            if idx >= 0:
                self.sensor_combo.setCurrentIndex(idx)
        self.sensor_combo.blockSignals(False)
        self.analyse()

    def _load_series(self, sensor_id: int):
        with session(self.engine) as s:
            rows = s.execute(
                select(MeasurementRow.timestamp, MeasurementRow.value)
                .where(MeasurementRow.sensor_id == sensor_id)
                .order_by(MeasurementRow.timestamp.desc())
                .limit(MAX_SAMPLES)
            ).all()
        if not rows:
            return None, None
        rows = rows[::-1]  # back to chronological
        # datetime.timestamp() raises OSError on Windows for out-of-range dates
        # (pre-1970 / epoch-zero in a positive-UTC zone / far future); skip those
        # rows so the Analysis tab degrades gracefully instead of crashing. Also
        # drop non-finite values (NaN/inf) that would poison the FFT.
        tvals, yvals = [], []
        for r in rows:
            v = r[1]
            if v is None or not math.isfinite(v):
                continue
            try:
                t = r[0].timestamp()
            except (OSError, OverflowError, ValueError):
                continue
            tvals.append(t)
            yvals.append(v)
        if not tvals:
            return None, None
        return np.array(tvals, dtype=float), np.array(yvals, dtype=float)

    @staticmethod
    def _estimate_fs(ts: np.ndarray) -> float | None:
        if ts.size < 2:
            return None
        dt = np.median(np.diff(ts))
        if np.isfinite(dt) and dt > 0:
            return 1.0 / dt
        # Timestamps quantised coarser than the sample rate (e.g. whole-second
        # stamps on faster data) give a median step of 0. Fall back to the
        # average rate over the whole record so the spectrum is still usable.
        span = float(ts[-1] - ts[0])
        if np.isfinite(span) and span > 0:
            return (ts.size - 1) / span
        return None

    def analyse(self):
        sensor_id = self.sensor_combo.currentData()
        self.fft_plot.clear()
        self.spec_img.clear()
        if sensor_id is None:
            self.info.setText("")
            return

        ts, y = self._load_series(sensor_id)
        if y is None or y.size < MIN_SAMPLES:
            self.info.setText("Not enough data for frequency analysis "
                              f"(need ≥ {MIN_SAMPLES} readings).")
            return
        fs = self._estimate_fs(ts)
        if fs is None:
            self.info.setText("Could not estimate the sampling rate from timestamps.")
            return

        n = y.size
        if float(np.ptp(y)) == 0.0:
            # A constant / DC / all-sentinel channel has no spectral content;
            # after DC removal it is all zeros and argmax would report a bogus
            # "dominant peak". Say so plainly instead.
            self.info.setText(f"{n:,} samples · fs ≈ {fs:.1f} Hz · no variation in "
                              "the signal (flat / constant / no-data channel).")
            return
        x = y - np.mean(y)  # remove DC / baseline offset before transforming

        # ---- amplitude spectrum ----
        win = np.hanning(n)
        spec = np.abs(np.fft.rfft(x * win)) * (2.0 / np.sum(win))
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        self.fft_plot.plot(freqs, spec, pen=pg.mkPen(COLORS["accent"], width=1.5))
        peak = float(freqs[int(np.argmax(spec[1:]) + 1)]) if spec.size > 1 else 0.0
        self.info.setText(
            f"{n:,} samples · estimated fs ≈ {fs:.1f} Hz · Nyquist {fs / 2:.1f} Hz "
            f"· dominant peak ≈ {peak:.2f} Hz")

        # ---- spectrogram (numpy STFT) ----
        self._draw_spectrogram(x, fs)

    def _draw_spectrogram(self, x: np.ndarray, fs: float):
        n = x.size
        nperseg = int(min(1024, max(64, 2 ** int(np.log2(max(n // 8, 64))))))
        if n < nperseg * 2:
            return  # too short for a meaningful spectrogram
        noverlap = nperseg // 2
        step = nperseg - noverlap
        win = np.hanning(nperseg)
        n_seg = 1 + (n - nperseg) // step
        segs = np.stack([x[i * step:i * step + nperseg] * win for i in range(n_seg)])
        mag = np.abs(np.fft.rfft(segs, axis=1))
        spec_db = 20.0 * np.log10(mag + 1e-9)  # shape (n_seg, n_freq) -> image [x=time, y=freq]

        self.spec_img.setImage(spec_db, autoLevels=False)
        vmax = float(spec_db.max())
        self.spec_img.setLevels([vmax - 80.0, vmax])  # 80 dB dynamic range
        duration = n / fs
        nyq = fs / 2.0
        self.spec_img.setRect(QRectF(0.0, 0.0, duration, nyq))
        self.spec_plot.setRange(xRange=(0, duration), yRange=(0, nyq), padding=0)
