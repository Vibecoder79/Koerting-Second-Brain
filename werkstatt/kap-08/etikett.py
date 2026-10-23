#!/usr/bin/env python3
"""Herkunftsetikett in abgeholten Dateien pruefen und fehlende als «unbekannt» fuellen. Blockiert nie.

    etikett.py --pruefen           meldet je Datei und zaehlt je Ort, was fehlt
    etikett.py --fuellen           traegt provenance.origin: unbekannt ein, wo der Kopf es nicht hat
Unbekannt gilt als Fremdinhalt. Die Zahl der «unbekannt» ist die Kennzahl; steigt sie, ist ein
Abholer falsch eingerichtet.
"""
import argparse
import os
import pathlib
import re

VAULT = pathlib.Path(os.environ.get("VAULT_DIR", "/opt/vault/work/vault"))
ORTE = ("08 Meeting Inbox", "Meetings", "Notizen")      # wo Maschinen von aussen ablegen
WERTE = ("ingested-external", "unbekannt")               # dazu ai-<werkzeug>, human-<kuerzel>
FELD = re.compile(r"^provenance:\n(?:[ \t]+.*\n)*?[ \t]+origin:\s*[\"']?([^\s\"']+)", re.M)   # auch in Anfuehrungszeichen
BLOCK = re.compile(r"^provenance:", re.M)                                                 # auch die Inline-Form {origin: x}


def abgeholt():
    for p in VAULT.rglob("*.md"):
        if any(t in p.parts for t in ORTE):
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--fuellen", action="store_true")
    a = ap.parse_args()
    je_ort, ok = {}, 0
    for p in abgeholt():
        ort = next(t for t in ORTE if t in p.parts)
        t = p.read_text(encoding="utf-8")
        kopf = t.split("\n---", 2)[0] if t.startswith("---\n") else None
        m = FELD.search(kopf or "")
        if kopf is None:
            lage = "OHNE KOPF"                                 # kein Datenkopf: melden, nicht fuellen
        elif m is None and BLOCK.search(kopf):
            lage = "BLOCK OHNE ORIGIN"                        # ein zweiter Block waere doppelt: melden
        elif m is None:
            lage = "FEHLT"
            if a.fuellen:
                p.write_text(t.replace("---\n", "---\nprovenance:\n  origin: unbekannt\n", 1), encoding="utf-8")
                lage = "GEFUELLT"
        elif not (m.group(1) in WERTE or m.group(1).startswith(("ai-", "human-"))):
            lage = f"UNGUELTIG «{m.group(1)}»"
        else:
            ok += 1; continue
        je_ort[ort] = je_ort.get(ort, 0) + 1
        print(f"{lage:20} {p.relative_to(VAULT)}")
    print(f"{ok} etikettiert; Befunde je Ort: " + (", ".join(f"{o}: {n}" for o, n in sorted(je_ort.items())) or "keine"))


if __name__ == "__main__":
    main()
