#!/usr/bin/env python3
"""Je H2-Abschnitt des Regelwerks die Kennzeile lesen: wer traegt ihn? Ein Abschnitt ohne Kennzeile ist ein Befund."""
import pathlib
import re
import sys

t = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "CLAUDE.md").read_text(encoding="utf-8")
teile = re.split(r"^## ", t, flags=re.M)[1:]
befund = 0
for teil in teile:
    titel = teil.split("\n", 1)[0].strip()
    m = re.search(r"<!--\s*getragen_von:\s*(.*?)\s*-->", teil)
    if not m:
        print(f"BEFUND  {titel}: keine Kennzeile"); befund += 1; continue
    wert = m.group(1)
    art = "landkarte" if wert.startswith("landkarte") else "prosa    " if wert.startswith("prosa") else "traeger  "
    print(f"{art}  {titel}: {wert}")
print(f"{len(teile)} Abschnitte, {befund} ohne Kennzeile")
sys.exit(1 if befund else 0)
