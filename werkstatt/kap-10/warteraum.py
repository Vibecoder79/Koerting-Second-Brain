#!/usr/bin/env python3
"""Der Warteraum: zaehlen, und ein Meeting von Hand an seinen Platz bringen. Kein Job liest hier.

    warteraum.py --zaehlen                                     Kennzahl fuer den Waechter: Zahl und Alter
    warteraum.py --datei "2026-10-21 Titel.md" --kuerzel BSP [--ausfuehren]
"""
import argparse
import datetime
import os
import pathlib
import sys

import zuordnung

VAULT = zuordnung.VAULT
WARTERAUM = VAULT / "08 Meeting Inbox"

ap = argparse.ArgumentParser()
ap.add_argument("--zaehlen", action="store_true"); ap.add_argument("--datei"); ap.add_argument("--kuerzel")
ap.add_argument("--ausfuehren", action="store_true")
a = ap.parse_args()
if a.zaehlen:
    dateien = [p for p in WARTERAUM.glob("*.md") if "Transkript" not in p.name]
    aeltestes = max((datetime.date.today() - datetime.date.fromtimestamp(p.stat().st_mtime)).days for p in dateien) if dateien else 0
    print(f"{len(dateien)} im Warteraum, aeltestes {aeltestes} Tage"); sys.exit(0)
reg = zuordnung.register()
if a.kuerzel not in reg:
    sys.exit(f"ABBRUCH: Kuerzel {a.kuerzel} nicht vergeben")
ziel = VAULT / reg[a.kuerzel] / "Meetings"
quellen = [q for q in (WARTERAUM / a.datei, WARTERAUM / a.datei.replace(".md", " — Transkript.md")) if q.exists()]
if not quellen:
    sys.exit(f"ABBRUCH: {a.datei} liegt nicht im Warteraum")
for q in quellen:
    if (ziel / q.name).exists():
        sys.exit(f"ABBRUCH: {q.name} liegt schon in {ziel.relative_to(VAULT)}; nichts verschoben")
for quelle in quellen:
    if True:
        print(f"{'VERSCHIEBE' if a.ausfuehren else 'TROCKEN   '} {quelle.name} -> {ziel.relative_to(VAULT)}/")
        if a.ausfuehren:
            ziel.mkdir(parents=True, exist_ok=True); quelle.rename(ziel / quelle.name)
