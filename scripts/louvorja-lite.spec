# -*- mode: python ; coding: utf-8 -*-
"""Bundle do LouvorJA Lite (PyInstaller, modo onedir).

onedir e não onefile: onefile reexplode dezenas de MB em /tmp a cada abertura do app, o que num
pendrive é lento sem necessidade. A pasta `data/` (banco + ~15 GB de mídia) NUNCA entra aqui —
ela fica ao lado do AppImage e é resolvida em tempo de execução (app/config.py).
"""

from pathlib import Path

RAIZ = Path(SPECPATH).parent

a = Analysis(
    [str(RAIZ / "app" / "launcher.py")],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=[(str(RAIZ / "app" / "static"), "app/static")],
    # O uvicorn resolve estes por string em tempo de execução, então o PyInstaller não os enxerga
    # sozinho — sem eles o servidor sobe e morre no primeiro request.
    hiddenimports=[
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.logging",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "playwright", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="louvorja-lite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="louvorja-lite",
)
