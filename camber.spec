# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Camber Windows build."""
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
HERE = os.path.abspath('.')

# Bundle non-Python package data (import profiles + sample dataset) preserving
# the camber/... layout so Path(__file__)-based lookups resolve in the build.
CAMBER_DATA = collect_data_files('camber', includes=['**/*.json', '**/*.csv'])

# Tiny bootstrap that imports camber as a package (fixes relative-import error)
BOOTSTRAP = os.path.join(HERE, '_camber_launcher.py')
if not os.path.exists(BOOTSTRAP):
    with open(BOOTSTRAP, 'w') as f:
        f.write("from camber.main import main\n"
                "if __name__ == '__main__':\n"
                "    main()\n")

a = Analysis(
    [BOOTSTRAP],
    pathex=[os.path.join(HERE, 'src')],
    binaries=[],
    datas=[
        ('camber_icon.ico', '.'),
        ('camber_icon.png', '.'),
    ] + CAMBER_DATA,
    hiddenimports=[
        'camber',
        'camber.main',
        'camber.logging_setup',
        'camber.ui.main_window',
        'camber.ui.dashboard_panel',
        'camber.ui.import_dialog',
        'camber.ui.theme',
        'camber.charts.chart_panel',
        'camber.charts.analysis_panel',
        'camber.integrations.sensor_import',
        'camber.mapping.map_panel',
        'camber.services.services',
        'camber.storage.db',
        'camber.extension_api.api',
        'camber.domain.models',
        'camber_convert',
        'camber_convert.readers.csv_reader',
        'camber_convert.readers.wide_csv_reader',
        'numpy',
        'uvicorn.logging',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'sqlalchemy.dialects.sqlite',
        'pyqtgraph',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Camber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='camber_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Camber',
)
