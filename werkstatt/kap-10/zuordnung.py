#!/usr/bin/env python3
"""Ordnet einen Titel «[KUERZEL] Thema» einem Ordner zu: Zeichenvergleich gegen die Datenkoepfe der Hubs.

    zuordnung.py --titel "[BSP] Statusmeeting"
Das Register entsteht bei jedem Aufruf aus den Hubs (Feld meeting_key) in allen Baeumen.
Kein Kuerzel, unbekanntes Kuerzel, mehrdeutiger Stamm oder leeres Thema heisst: Warteraum.
"""
import argparse
import os
import pathlib
import re

VAULT = pathlib.Path(os.environ.get("VAULT_DIR", "/opt/vault/work/vault"))
MUSTER = re.compile(r"^\s*\[([A-Z0-9-]{2,})\]\s*(.*)$")
FELD = re.compile(r"^meeting_key:\s*([A-Z0-9-]+)\s*$", re.M)
ABHOLORTE = ("08 Meeting Inbox", "Meetings", "Notizen", "Vorlagen")   # dort schreiben Maschinen, kein Hub


def dateiname(text):
    """Nur Buchstaben, Ziffern, Leerzeichen und Bindestrich: kein Pfad aus Fremdtext, keine Klammern
    (ein Wikilink mit eckigen Klammern im Namen loest sich in Obsidian nicht auf)."""
    return re.sub(r"[^\w\s-]", "", text).strip()[:120]


def datenkopf(p):
    t = p.read_text(encoding="utf-8", errors="replace")[:4000]
    return t.split("\n---", 1)[0] if t.startswith("---\n") else ""


def register():
    """Kuerzel -> Ordner, nur aus dem Datenkopf von Hubs; Abholorte zaehlen nicht. Ein Kuerzel an
    zwei Hubs ist eine Kollision: melden und nicht zuordnen."""
    reg, kollision = {}, set()
    for p in sorted(VAULT.rglob("*.md")):
        if p.parts[len(VAULT.parts)].startswith(".") or any(o in p.parts for o in ABHOLORTE):
            continue
        m = FELD.search(datenkopf(p))
        if not m:
            continue
        ordner = p.parent.relative_to(VAULT).as_posix()
        if m.group(1) in reg and reg[m.group(1)] != ordner:
            kollision.add(m.group(1))
        reg[m.group(1)] = ordner
    for k in kollision:
        print(f"KOLLISION: Kuerzel {k} an mehreren Hubs; wird nicht zugeordnet")
        reg.pop(k)
    return reg


def ordne_zu(titel, reg):
    """(zielordner, grund); None heisst Warteraum."""
    m = MUSTER.match(titel or "")
    if not m:
        return None, "kein Kuerzel im Titel; erwartet [KUERZEL] Thema"
    k, thema = m.group(1), m.group(2).strip()
    if k not in reg:
        return None, f"Kuerzel {k} ist nicht vergeben"
    if not thema:
        return None, f"Kuerzel {k} erkannt, aber kein Thema"
    mehrdeutig = [x for x in reg if x != k and x.startswith(k + "-")]
    if mehrdeutig:
        return None, f"{k} ist Praefix von {mehrdeutig}: mehrdeutig"
    return reg[k], f"{k} -> {reg[k]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--titel", required=True)
    ziel, grund = ordne_zu(ap.parse_args().titel, register())
    print(("WARTERAUM: " if ziel is None else "ZIEL: ") + grund)
