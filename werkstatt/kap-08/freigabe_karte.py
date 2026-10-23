#!/usr/bin/env python3
"""Aus einem Vorschlag eine Freigabekarte machen: eine Zeile in der Liste, die der Flow anzeigt.

    freigabe_karte.py --vorschlag vorschlaege/BSP-2026-10-21-1.md [--trocken]
Die Liste ist eine Datei (Attrappe fuer eine SharePoint-Liste). Je Kennung eine Zeile; eine
zweite wird verweigert. Der Server schreibt nur feste Felder.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys

LISTE = pathlib.Path(os.environ.get("FREIGABE_LISTE", "/opt/vault/freigabe-liste.json"))
VAULT = pathlib.Path(os.environ.get("VAULT_DIR", "/opt/vault/work/vault"))
KUERZEL = re.compile(r"^meeting_key:\s*([A-Z0-9-]+)\s*$", re.M)


ABHOLORTE = ("08 Meeting Inbox", "Meetings", "Notizen", "Vorlagen")   # dort schreiben Maschinen, kein Hub


def datenkopf(p):
    t = p.read_text(encoding="utf-8", errors="replace")[:4000]
    return t.split("\n---", 1)[0] if t.startswith("---\n") else ""


def register():
    """Kuerzel -> Projektordner, nur aus dem Datenkopf von Hubs. Ein Kuerzel an zwei Orten ist
    eine Kollision und wird nicht zugeordnet; das Ziel kommt nie aus dem Vorschlag selbst."""
    reg, kollision = {}, set()
    for p in sorted(VAULT.rglob("*.md")):
        if p.parts[len(VAULT.parts)].startswith(".") or any(o in p.parts for o in ABHOLORTE):
            continue
        m = KUERZEL.search(datenkopf(p))
        if m:
            ordner = p.parent.relative_to(VAULT).as_posix()
            if m.group(1) in reg and reg[m.group(1)] != ordner:
                kollision.add(m.group(1))
            reg[m.group(1)] = ordner
    for k in kollision:
        print(f"KOLLISION: Kuerzel {k} an mehreren Hubs; wird nicht zugeordnet", file=sys.stderr); reg.pop(k)
    return reg


def bereinigt(titel):
    return re.sub(r"[^\w\s-]", "", titel).strip()[:120]


def liste_lesen():
    return json.loads(LISTE.read_text(encoding="utf-8")) if LISTE.exists() else []


def liste_schreiben(zeilen):
    tmp = LISTE.with_suffix(".tmp")
    tmp.write_text(json.dumps(zeilen, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, LISTE)


def vorschlag_lesen(pfad):
    t = pathlib.Path(pfad).read_text(encoding="utf-8")
    kopf, rumpf = t.split("\n---\n", 1)
    felder = dict(re.findall(r"^(\w+):\s*(.*)$", kopf, re.M))
    for pflicht in ("kennung", "kuerzel", "titel"):
        if not felder.get(pflicht):
            sys.exit(f"ABBRUCH: Vorschlag ohne {pflicht}")
    if not re.fullmatch(r"[A-Z0-9-]+", felder["kennung"]):
        sys.exit(f"ABBRUCH: Kennung «{felder['kennung']}» darf nur Grossbuchstaben, Ziffern und Bindestrich tragen")
    if felder["kuerzel"] not in register():
        sys.exit(f"ABBRUCH: Kuerzel {felder['kuerzel']} ist nicht vergeben; kein Ziel aus dem Vorschlag")
    def abschnitt(name):
        m = re.search(rf"^## {name}[ \t]*\n(?:[ \t]*\n)*((?:- .*\n?)*)", rumpf, re.M)   # Leerzeile nach der Ueberschrift erlaubt
        return [z[2:].strip() for z in m.group(1).splitlines()] if m else []
    beschluesse, aufgaben = abschnitt("Beschlüsse"), abschnitt("Aufgaben")
    if not beschluesse and not aufgaben:
        sys.exit("ABBRUCH: Vorschlag ohne Beschluesse und ohne Aufgaben; eine leere Karte fragt nichts")
    return felder, beschluesse, aufgaben


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vorschlag", required=True)
    ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    felder, beschluesse, aufgaben = vorschlag_lesen(a.vorschlag)
    zeilen = liste_lesen()
    schon = [z for z in zeilen if z["kennung"] == felder["kennung"]]
    if schon:      # je Kennung genau eine Zeile; eine neue Runde bekommt eine neue Kennung
        sys.exit(f"ABBRUCH: zu {felder['kennung']} gibt es schon eine Karte (verdikt={schon[0]['verdikt']}, verarbeitet={schon[0]['verarbeitet']}); keine zweite")
    karte = {
        "kennung": felder["kennung"], "titel": bereinigt(felder["titel"]), "kuerzel": felder["kuerzel"],
        "karte_text": "Beschlüsse:\n" + "\n".join(f"- {b}" for b in beschluesse)
                      + "\nAufgaben:\n" + "\n".join(f"- {t}" for t in aufgaben),
        "verdikt": "offen", "kommentar": "", "entschieden_am": "",      # ab hier gehoert das dem Flow
        "angelegt_am": datetime.date.today().isoformat(),
        "verarbeitet": "nein",                                          # setzt der Server, nach der Wirkung
    }
    print(("TROCKEN: " if a.trocken else "KARTE: ") + json.dumps(karte, ensure_ascii=False)[:160] + " …")
    if a.trocken:
        return
    zeilen.append(karte)
    liste_schreiben(zeilen)
    print(f"Karte fuer {felder['kennung']} liegt in der Liste; der Flow zeigt sie an.")


if __name__ == "__main__":
    main()
