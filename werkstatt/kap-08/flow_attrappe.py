#!/usr/bin/env python3
"""Attrappe fuer den Flow: der Klick des Menschen auf der Karte. Setzt verdikt, kommentar, entschieden_am."""
import datetime
import sys
from freigabe_karte import liste_lesen, liste_schreiben

kennung, verdikt = sys.argv[1], sys.argv[2]
zeilen = liste_lesen()
treffer = 0
for z in zeilen:
    if z["kennung"] == kennung and z["verarbeitet"] == "nein":
        z.update(verdikt=verdikt, entschieden_am=datetime.date.today().isoformat(),
                 kommentar=sys.argv[3] if len(sys.argv) > 3 else "")
        treffer += 1
if not treffer:
    sys.exit(f"Flow: keine wartende Karte {kennung}")
liste_schreiben(zeilen); print(f"Flow: {kennung} -> {verdikt}")
