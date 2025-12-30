# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all


ROOT = os.path.abspath(os.path.dirname(__file__))

datas = []
binaries = []
hiddenimports = []

pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")
datas += pyside6_datas
binaries += pyside6_binaries
hiddenimports += pyside6_hidden

datas += [
    (os.path.join(ROOT, "gui", "IKK_logo.svg"), "gui"),
]

a = Analysis(
    [os.path.join(ROOT, "gui", "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FDM-Migration",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FDM-Migration",
)
