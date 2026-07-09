"""Map panel — dark Leaflet tiles with status markers."""
from __future__ import annotations
import json
import math
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from ..services.services import AssetService, StatusService
from ..ui.theme import COLORS

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html,body,#map{height:100%;margin:0;background:""" + COLORS["bg_primary"] + """}
  .leaflet-popup-content-wrapper{background:#1C2333;color:#E6EDF3;border:1px solid #30363D;border-radius:6px}
  .leaflet-popup-tip{background:#1C2333}
  .leaflet-popup-content{font-family:'Segoe UI',monospace;font-size:12px}
  .popup-name{font-weight:bold;font-size:14px;margin-bottom:4px}
  .popup-status{text-transform:uppercase;font-weight:bold;letter-spacing:1px}
</style>
</head><body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const assets = __ASSETS__;
const colors = {ok:"#2ECC71",warning:"#F1C40F",critical:"#E74C3C",unknown:"#6E7681"};
const map = L.map('map',{zoomControl:true}).setView([44.81,20.46],11);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{
  attribution:'CartoDB',maxZoom:19
}).addTo(map);
const bounds=[];
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
assets.forEach(a=>{
  if(a.latitude==null||a.longitude==null||!isFinite(a.latitude)||!isFinite(a.longitude))return;
  const c=colors[a.status]||colors.unknown;
  L.circleMarker([a.latitude,a.longitude],{
    radius:10,color:c,weight:2,fillColor:c,fillOpacity:0.3
  }).bindPopup(`<div class="popup-name">${esc(a.name)}</div>
    <div>${esc(a.type)}</div>
    <div class="popup-status" style="color:${c}">${esc(a.status)}</div>`).addTo(map);
  bounds.push([a.latitude,a.longitude]);
});
if(bounds.length){map.fitBounds(bounds,{padding:[50,50]});}
else{
  const d=document.createElement('div');
  d.style.cssText='position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:1000;'
    +'background:#1C2333;color:#E6EDF3;border:1px solid #30363D;border-radius:6px;'
    +'padding:8px 14px;font:12px Segoe UI,sans-serif';
  d.textContent=assets.length?'No coordinates set for these assets yet.':'No assets yet.';
  document.body.appendChild(d);
}
</script></body></html>"""


class MapPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.assets_svc = AssetService(engine)
        self.status_svc = StatusService(engine)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("ASSET MAP")
        title.setObjectName("labelHeader")
        top.addWidget(title)
        top.addStretch()
        btn = QPushButton("Refresh Map")
        btn.clicked.connect(self.refresh)
        top.addWidget(btn)
        layout.addLayout(top)

        self.view = QWebEngineView()
        layout.addWidget(self.view)
        self.refresh()

    def refresh(self):
        assets = self.assets_svc.list_assets()
        statuses = {s["asset_id"]: s["status"] for s in self.status_svc.asset_statuses()}
        for a in assets:
            a["status"] = statuses.get(a["id"], "unknown")
            # Non-finite coordinates serialise to bare NaN/Infinity (invalid JSON,
            # and would reach L.circleMarker([NaN,...])); drop them to null.
            for k in ("latitude", "longitude"):
                v = a.get(k)
                if not isinstance(v, (int, float)) or not math.isfinite(v):
                    a[k] = None
        # "</" -> "<\/" so an asset name containing "</script>" can't close the
        # inline <script> block and blank the map.
        payload = json.dumps(assets).replace("</", "<\\/")
        html = HTML_TEMPLATE.replace("__ASSETS__", payload)
        self.view.setHtml(html)
