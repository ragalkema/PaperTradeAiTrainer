# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "Dashboard" / "src" / "dashboard" / "main.py")],
    pathex=[
        str(root / "Dashboard" / "src"),
        str(root / "PaperTrading" / "src"),
        str(root / "shared" / "src"),
    ],
    datas=[(str(root / "Dashboard" / "assets"), "Dashboard/assets")],
    hiddenimports=["dashboard", "paper_trading", "shared"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaperTradeAiTrainer",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PaperTradeAiTrainer")
