# -*- mode: python ; coding: utf-8 -*-
# Onefile build for the CyberleekViewer chain-viewer GUI.
# Reads everything from Solana mainnet RPC; no external services needed at runtime.

a = Analysis(
    ['app.py'],
    pathex=['.venv/Lib/site-packages', '.'],
    binaries=[],
    datas=[
        ('.venv/Lib/site-packages/customtkinter', 'customtkinter'),
        ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=['customtkinter', 'solders'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PIL'],
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
    name='CyberleekViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
