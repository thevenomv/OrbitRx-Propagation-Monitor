# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../app.py'],
    pathex=['../src'],
    binaries=[],
    datas=[('../src/orbitrx/assets/bundled/world_map.jpg', 'orbitrx/assets/bundled')],
    hiddenimports=[
        'serial', 'customtkinter', 'tkcalendar', 'matplotlib',
        'matplotlib.backends.backend_tkagg', 'PIL', 'win10toast', 'winsound',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OrbitRxMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
