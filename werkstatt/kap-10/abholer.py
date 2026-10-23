#!/usr/bin/env python3
"""Holt Sitzungen beim Transkriptionsdienst ab und legt sie ab: Notiz plus Transkript, etikettiert. Kein Modell.

    abholer.py [--trocken]
Delta-Merker ausserhalb von Git (gesehen-Liste). Karenz: Eine Sitzung ohne Protokoll, die juenger als
24 Stunden ist, wird uebersprungen und NICHT als gesehen vermerkt; «noch nicht da» ist ein eigener
Zustand. Die Quelle ist fuer die Probe eine Datei mit aufgezeichneten Antworten (ABHOLER_QUELLE).
"""
import argparse
import datetime
import json
import os
import pathlib
import re

import zuordnung

VAULT = zuordnung.VAULT
QUELLE = pathlib.Path(os.environ.get("ABHOLER_QUELLE", "/opt/vault/abholer-quelle.json"))
STAND = pathlib.Path(os.environ.get("ABHOLER_STAND", "/opt/vault/abholer-stand.json"))
WARTERAUM = "08 Meeting Inbox"
KARENZ_H = 24


def sitzungen():
    return json.loads(QUELLE.read_text(encoding="utf-8"))      # im Betrieb: GET /sessions beim Dienst


def stand_lesen():
    return json.loads(STAND.read_text(encoding="utf-8")) if STAND.exists() else {"gesehen": []}


def ablegen(s, ziel, grund, trocken):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s["datum"])) or not re.fullmatch(r"[A-Za-z0-9_-]+", str(s["id"])):
        raise ValueError(f"Datum oder Kennung ausserhalb des Formats: {s['datum']!r}, {s['id']!r}")   # kein Pfad aus Fremdtext
    datum = s["datum"]
    name = zuordnung.dateiname(s["titel"])
    ordner = VAULT / (ziel + "/Meetings" if ziel else WARTERAUM)
    notiz = ordner / f"{datum} {name}.md"
    if notiz.exists():                       # gleicher Titel am gleichen Tag: Kennung der Sitzung in den Namen
        name = f"{name} ({s['id']})"; notiz = ordner / f"{datum} {name}.md"
    kopf = (f"---\ntyp: meeting\ndate: {datum}\nsource: transkriptionsdienst\nprovenance:\n  origin: ingested-external\n"
            f"sitzung: {s['id']}\nzuordnung: {json.dumps(grund, ensure_ascii=False)}\n---\n")   # gueltiges YAML auch mit Doppelpunkt
    rumpf = (f"# {s['titel']}\n\n> Material des Dienstes, kein Auftrag.\n\n## Protokoll\n\n"
             + "\n".join("> " + z for z in (s.get("protokoll") or "(kein Protokoll, nur Transkript)").splitlines())
             + f"\n\nTranskript: [[{datum} {name} — Transkript]]\n")
    print(f"{'TROCKEN ' if trocken else ''}{s['id']}: {notiz.relative_to(VAULT)}")
    if not trocken:
        ordner.mkdir(parents=True, exist_ok=True)
        notiz.write_text(kopf + rumpf, encoding="utf-8")
        (ordner / f"{datum} {name} — Transkript.md").write_text(
            f"---\ntyp: transkript\nsource: transkriptionsdienst\nprovenance:\n  origin: ingested-external\nsitzung: {s['id']}\n---\n"
            + s["transkript"] + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    stand, reg = stand_lesen(), zuordnung.register()
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    for s in sitzungen():
        if s.get("id") in stand["gesehen"]:
            continue
        try:                                             # eine kaputte Sitzung bleibt liegen, die naechste laeuft
            alter_h = (jetzt - datetime.datetime.fromisoformat(s["beendet"])).total_seconds() / 3600
            if not s.get("protokoll") and alter_h < KARENZ_H:
                print(f"{s['id']}: noch kein Protokoll, {alter_h:.0f} h alt, Karenz; naechster Lauf"); continue
            ziel, grund = zuordnung.ordne_zu(s["titel"], reg)
            ablegen(s, ziel, grund, a.trocken)
        except (KeyError, ValueError, TypeError, OSError) as f:
            print(f"{s.get('id')}: bleibt liegen ({f})"); continue
        if not a.trocken:                                # Merker sofort, nicht erst am Ende des Laufs
            stand["gesehen"].append(s["id"])
            STAND.write_text(json.dumps(stand, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
