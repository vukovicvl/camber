"""Generate the Camber tester's user guide as a PDF.

Uses only PySide6 (already a Camber dependency) — no reportlab/weasyprint, which
have no wheels for Python 3.14. Renders an HTML document to a paginated A4 PDF
via QTextDocument -> QPdfWriter.

Run:  python docs/make_user_guide.py
Out:  docs/Camber_User_Guide.pdf
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Use the native platform, not "offscreen": the offscreen QPA plugin has no
# real font backend, so QTextDocument.print_ rasterises the page (glyphs become
# .notdef boxes). The native platform embeds real vector fonts even headless.
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "")
if not os.environ["QT_QPA_PLATFORM"]:
    del os.environ["QT_QPA_PLATFORM"]

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize, QPageLayout, QImage
from PySide6.QtCore import QSizeF, QMarginsF, QUrl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ICON = ROOT / "camber_icon.png"
OUT = HERE / "Camber_User_Guide.pdf"

CSS = """
* { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }
body { color: #1c2733; font-size: 10.5pt; line-height: 150%; }
h1 { font-size: 30pt; color: #0e7c86; margin-top: 0; margin-bottom: 2pt; }
h2 { font-size: 17pt; color: #0e7c86; margin-top: 22pt; margin-bottom: 4pt;
     border-bottom: 2px solid #d7e3e6; padding-bottom: 3pt; }
h3 { font-size: 12.5pt; color: #16505a; margin-top: 14pt; margin-bottom: 2pt; }
p  { margin-top: 4pt; margin-bottom: 4pt; }
.lead { font-size: 12pt; color: #33454f; }
.tag { color: #5a6b76; font-size: 10pt; }
.muted { color: #6b7a84; }
code, .mono { font-family: 'Consolas', 'Courier New', monospace; font-size: 9.5pt;
              background-color: #eef3f4; color: #0d3b41; }
pre { font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt;
      background-color: #0e2126; color: #d7f0f2; padding: 8pt; }
.note { background-color: #eaf6f7; padding: 8pt; }
.warn { background-color: #fdf1e6; padding: 8pt; }
table { border-collapse: collapse; }
th { background-color: #0e7c86; color: #ffffff; padding: 5pt 8pt; text-align: left; font-size: 10pt; }
td { padding: 5pt 8pt; border-bottom: 1px solid #dbe4e7; font-size: 10pt; }
.step { color: #0e7c86; font-weight: bold; }
a { color: #0e7c86; }
"""

# NOTE: Qt rich text is an HTML subset — inline styles + simple tables only.
BODY = r"""
<table width="100%"><tr>
  <td width="72"><img src="camber_icon" width="64" height="64"></td>
  <td>
    <h1>Camber</h1>
    <div class="lead">Structural Health Monitoring &mdash; Tester&rsquo;s Guide</div>
    <div class="tag">Version 0.1.0 &nbsp;&bull;&nbsp; Windows desktop &nbsp;&bull;&nbsp;
        Everything runs on your PC &mdash; your data never leaves your computer.</div>
  </td>
</tr></table>

<p class="lead" style="margin-top:14pt;">Thank you for testing Camber. This guide walks you
through installing the app, loading data, viewing and analysing sensor readings, and sending
feedback. No prior setup or internet connection is required.</p>

<h2>1. What Camber is</h2>
<p>Camber is an open platform for <b>structural health monitoring (SHM)</b> &mdash; watching how
a bridge (or other structure) behaves through data from its sensors: strain gauges,
accelerometers, inclinometers, temperature and wind sensors, and more.</p>
<p>With Camber you can <b>import a raw sensor recording</b> (a CSV export from a data logger),
have the app <b>detect the layout automatically</b> and create the asset and its sensors, then
<b>chart, monitor and analyse</b> the readings &mdash; including a <b>Live</b> view and an
<b>FFT / spectrogram</b> for vibration analysis.</p>

<h2>2. Installing &amp; running</h2>
<p>Camber is delivered as a standard <b>Windows installer</b>, <code>Camber_Setup.exe</code>.</p>
<p><span class="step">1.</span> Double-click <code>Camber_Setup.exe</code>.
   If Windows shows a &ldquo;Windows protected your PC&rdquo; (SmartScreen) notice on an
   unsigned build, click <b>More info &rarr; Run anyway</b>. It installs for your user only
   and does not need administrator rights.</p>
<p><span class="step">2.</span> Finish the wizard. You get a <b>Start Menu</b> entry and,
   if you ticked it, a <b>Desktop</b> shortcut.</p>
<p><span class="step">3.</span> Launch <b>Camber</b>. The main window opens; a small local
   service also starts in the background at <code>http://127.0.0.1:8765</code> (used only on
   this machine &mdash; see &sect;11 Privacy).</p>
<div class="note"><b>First run.</b> The app starts with an empty inventory. The fastest way to
   see it working is <b>Data &rarr; Load sample data</b> (&sect;4).</div>

<h2>3. The window at a glance</h2>
<p>Camber is organised into tabs, plus a small menu bar (<b>Data</b> and <b>Help</b>) at the top.</p>
<table width="100%">
<tr><th width="90">Tab</th><th>What it shows</th></tr>
<tr><td><b>Dashboard</b></td><td>A summary of your assets and their overall status.</td></tr>
<tr><td><b>Assets</b></td><td>Your inventory of structures. Import files here, and
    <b>Rename</b> / <b>Delete</b> assets.</td></tr>
<tr><td><b>Status</b></td><td>Per-sensor OK / Warning / Critical against threshold rules.</td></tr>
<tr><td><b>Charts</b></td><td>Time-series plot of a chosen sensor, with a <b>Live</b> mode.</td></tr>
<tr><td><b>Analysis</b></td><td>Frequency analysis &mdash; FFT spectrum and spectrogram
    (best on accelerometers).</td></tr>
<tr><td><b>Map</b></td><td>Asset locations on a map (when coordinates are known).</td></tr>
</table>
<p style="margin-top:8pt;"><b>Menu bar.</b> <b>Data &rarr; Load sample data</b> loads a bundled
example recording. <b>Help &rarr; View logs folder</b> opens the folder with the app&rsquo;s log
files, <b>Help &rarr; Report an issue</b> opens the feedback page, and <b>Help &rarr; About</b>
shows the version and log location.</p>

<h2>4. Quick start in 60 seconds</h2>
<p><span class="step">1.</span> Open Camber. <span class="step">2.</span> Click the menu
<b>Data &rarr; Load sample data</b>. A confirmation reports how many readings and sensors were
loaded into &ldquo;V&auml;nersborg Bridge (sample)&rdquo;.</p>
<p><span class="step">3.</span> Go to the <b>Charts</b> tab, pick a sensor (e.g. an accelerometer
<code>A1</code>&ndash;<code>A5</code>), and click <b>Refresh</b>.</p>
<p><span class="step">4.</span> Tick <b>Live</b>, then click <b>Demo feed</b> to watch new
readings stream in. <span class="step">5.</span> Open the <b>Analysis</b> tab and pick an
accelerometer to see its frequency spectrum. That&rsquo;s the whole loop.</p>

<h2>5. Importing your own sensor files</h2>
<p>Camber reads <b>CSV</b> files. There are two buttons on the <b>Assets</b> tab.</p>

<h3>Import sensor file&hellip; (recommended)</h3>
<p>Use this for a <b>raw recording from a data logger</b> &mdash; including a <b>wide</b>,
multi-channel file where each column is a channel (<code>ch_1, ch_2, &hellip;</code>). Camber:</p>
<p>&bull; auto-detects the <b>delimiter</b> (comma, semicolon or tab), the <b>decimal mark</b>
(<code>.</code> or <code>,</code>), the text encoding and the timestamp format &mdash; so files
from different countries and vendors import correctly;<br>
&bull; shows a <b>preview</b> of the detected layout before importing; and<br>
&bull; <b>creates the asset and its sensors for you</b>, so you don&rsquo;t set anything up
by hand.</p>
<p>In the preview dialog you can review the detected format and warnings, then choose to import
into a <b>new asset</b> (give it a name) or an <b>existing</b> one. Click <b>Import</b> and a
progress dialog tracks the readings as they load.</p>

<h3>The import profile (for known loggers)</h3>
<p>A <b>profile</b> is a small mapping that tells Camber what each column means (e.g.
&ldquo;<code>ch_1</code>&nbsp;=&nbsp;strain gauge SG1 in &micro;m/m&rdquo;). Camber ships with a
profile for the V&auml;nersborg-style 30-channel logger and matches it automatically. You can add
your own profiles for a recurring file format &mdash; ask us and we&rsquo;ll help you write one.</p>

<h3>Import CSV (tidy files)</h3>
<p>Use the plain <b>Import CSV</b> button when you already have a <b>tidy</b> measurements file
with the columns <code>sensor_id, timestamp, metric_type, value, unit</code>, aimed at sensors
that already exist. If you pick a raw multi-channel file here by mistake, Camber tells you to use
<b>Import sensor file&hellip;</b> instead.</p>

<div class="note"><b>Tip.</b> If an import ever fails, note the message and check
<b>Help &rarr; View logs folder</b> &mdash; the full detail is written there, which helps us fix
the file quickly.</div>

<h2>6. Charts &mdash; viewing time series</h2>
<p>On the <b>Charts</b> tab, choose a <b>Sensor</b> from the drop-down and click <b>Refresh</b>.
The plot shows that sensor&rsquo;s readings over time. If a threshold rule exists for the metric,
you&rsquo;ll see shaded <b>warning</b> and <b>critical</b> bands and the points coloured by status.</p>
<p>You can zoom (mouse wheel), pan (drag), and right-click the plot for view options. Large
recordings are drawn as a fast down-sampled line automatically.</p>

<h2>7. Live mode</h2>
<p>Tick the <b>Live</b> checkbox to make the chart <b>auto-refresh and follow the latest
readings</b> as they arrive. This is how a real, always-on bridge sensor would appear.</p>
<p>To see Live mode without hardware, click <b>Demo feed</b>: Camber generates realistic
synthetic readings for the selected sensor so you can watch the live chart move. Turn it off to
stop. (Connecting real sensors is covered in &sect;10.)</p>

<h2>8. Analysis &mdash; FFT &amp; spectrogram</h2>
<p>The <b>Analysis</b> tab turns a vibration signal into its <b>frequencies</b> &mdash; useful
for finding a structure&rsquo;s natural (modal) frequencies. Pick an <b>accelerometer</b>, and
Camber computes:</p>
<p>&bull; an <b>FFT amplitude spectrum</b> (how much energy sits at each frequency), and<br>
&bull; a <b>spectrogram</b> (how that spectrum changes over time).</p>
<p>The sampling rate is estimated automatically from the timestamps, so you normally don&rsquo;t
enter anything. Peaks in the spectrum correspond to the structure&rsquo;s vibration modes.</p>

<h2>9. Managing assets</h2>
<p>On the <b>Assets</b> tab, select a row and use:</p>
<p>&bull; <b>Rename</b> &mdash; give the asset a clearer name.<br>
&bull; <b>Delete</b> &mdash; remove the asset <b>and all its sensors and measurements</b>. You are
asked to confirm; this cannot be undone.<br>
&bull; <b>Refresh</b> &mdash; reload the list.</p>

<h2>10. Connecting real live sensors (advanced)</h2>
<p>Camber has a small <b>local ingest API</b> that live readings are pushed to. It listens only on
this PC at <code>http://127.0.0.1:8765</code>. The Demo feed and the replay tool both use it, and a
real <b>sensor gateway</b> would use the same path.</p>
<p><b>Push one reading</b> &mdash; send a JSON <code>POST</code> to <code>/measurements</code>:</p>
<pre>{ "sensor_id": 12, "value": 0.83, "metric_type": "acceleration", "unit": "m/s2" }</pre>
<p><b>Push many at once</b> &mdash; <code>POST</code> a JSON list to <code>/measurements/batch</code>.
Ticking <b>Live</b> on the Charts tab then shows them arriving.</p>
<p><b>Replay a recording as if it were live</b> &mdash; a helper script plays an existing CSV back
through the API at a chosen rate:</p>
<pre>python scripts\replay_csv.py --list                       # list assets
python scripts\replay_csv.py RECORDING.csv --asset-id 3   # replay into asset 3</pre>
<div class="note"><b>Connecting actual hardware.</b> A &ldquo;gateway&rdquo; is a small program that
reads from your data logger (over a folder it writes CSVs to, or a protocol such as MQTT / Modbus /
a vendor SDK) and forwards each reading to the endpoint above. Camber does not talk to a specific
logger yet &mdash; tell us your hardware and we&rsquo;ll build the gateway for it.</div>

<h2>11. Privacy &mdash; where your data lives</h2>
<p>Camber is a <b>desktop application</b>. Your sensor data is stored in a local database file on
your own computer and is <b>never uploaded anywhere</b>. There is no account, no cloud, and no
website. The background service is bound to <code>127.0.0.1</code> (loopback), meaning it is
reachable only from your own machine &mdash; not from the network or the internet.</p>

<h2>12. Troubleshooting &amp; feedback</h2>
<p>&bull; <b>Something looks wrong or the app shows an error dialog.</b> The app keeps running and
writes details to a log file. Open <b>Help &rarr; View logs folder</b> and send us the newest
<code>.log</code> file.</p>
<p>&bull; <b>Report an issue.</b> Use <b>Help &rarr; Report an issue</b>, or email us, with: what you
did, what you expected, what happened, and (if possible) the file you imported and the log.</p>
<p>&bull; <b>An import failed.</b> Almost always a file-format detail &mdash; send the first few rows
of the CSV and the log, and we&rsquo;ll add support for it.</p>

<h2>13. Known limits</h2>
<p>This is an early (v0.1) build for evaluation. It is well suited to <b>campaign and event data</b>
&mdash; recordings and monitoring of bridges over hours, days or specific events. It is <b>not yet</b>
built for permanently streaming very high-rate data (e.g. continuous 200&nbsp;Hz from many channels
forever); that path (columnar storage, streaming, automated modal analysis) is on the roadmap. If you
hit a limit, that is useful feedback &mdash; please tell us.</p>

<p class="muted" style="margin-top:20pt;">Camber &mdash; open structural health monitoring.
Local API: http://127.0.0.1:8765 &nbsp;&bull;&nbsp; This guide covers version 0.1.0.</p>
"""


def build_pdf() -> Path:
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841

    writer = QPdfWriter(str(OUT))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(16, 15, 16, 16), QPageLayout.Unit.Millimeter)
    writer.setTitle("Camber User Guide")

    doc = QTextDocument()
    doc.setDefaultStyleSheet(CSS)
    if ICON.exists():
        img = QImage(str(ICON))
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl("camber_icon"), img)
    doc.setHtml("<html><body>" + BODY + "</body></html>")

    # Leave the document page size unset: QTextDocument.print_ then derives it
    # from the writer's printable rect (scaled to the layout DPI) and paginates.
    # Setting it manually to device pixels makes print_ over-scale to one page.
    doc.print_(writer)
    return OUT


if __name__ == "__main__":
    out = build_pdf()
    size_kb = out.stat().st_size / 1024 if out.exists() else 0
    print(f"Wrote {out}  ({size_kb:.0f} KB)")
