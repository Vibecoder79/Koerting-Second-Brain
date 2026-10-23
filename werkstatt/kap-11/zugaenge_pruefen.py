#!/usr/bin/env python3
"""Haelt das Register der Zugaenge gegen den Server, in beide Richtungen. Liest nur, nennt nie einen Wert.

    zugaenge_pruefen.py [--tage 60] [--bericht]

Befunde: Datei ohne Zeile, Zeile ohne Datei, Leser ohne Eintrag, Eintrag ohne Leser,
Ablauf unbekannt, Ablauf nah oder vorbei, Schluessel ohne Ablauf und ohne Rotationsdatum.
Rueckgabe 0 ohne Befund, 77 mit Befund. --bericht gibt die eine Zeile fuer den Tagesbericht.
"""
import argparse
import csv
import datetime
import os
import pathlib
import re
import sys

REGISTER = pathlib.Path(os.environ.get("ZUGAENGE_REGISTER", "zugaenge.tsv"))
SECRETS = pathlib.Path(os.environ.get("SECRETS_DIR", "/opt/vault/secrets"))
WERKZEUGE = pathlib.Path(os.environ.get("WERKZEUGE_DIR", "."))


def zeilen():
    with REGISTER.open(encoding="utf-8") as f:
        return list(csv.DictReader((z for z in f if not z.startswith("#")), delimiter="\t"))


def leser_im_code():
    """Welches Skript nennt welche Zugangsdatei im Quelltext."""
    treffer = {}
    for p in list(WERKZEUGE.glob("*.py")) + list(WERKZEUGE.glob("*.sh")):
        for name in re.findall(r"[\w-]+\.(?:env|pem|json)", p.read_text(encoding="utf-8", errors="replace")):
            treffer.setdefault(name, set()).add(p.name)
    return treffer


def pruefen(tage):
    befunde, heute, naechster = [], datetime.date.today(), None
    register = zeilen()
    dateien = {p.name for p in SECRETS.iterdir() if p.is_file()} if SECRETS.is_dir() else set()
    gefuehrt = {z["datei"] for z in register if z["art"] == "datei"}
    for d in sorted(dateien - gefuehrt):
        befunde.append(f"Datei ohne Zeile: {d}")
    for d in sorted(gefuehrt - dateien):
        befunde.append(f"Zeile ohne Datei: {d}")
    nennt = leser_im_code()
    for z in register:
        if z["art"] == "datei":
            soll = {l.strip() for l in z["leser"].split(",") if l.strip()}
            ist = nennt.get(z["datei"], set())
            for l in sorted(ist - soll):
                befunde.append(f"Leser ohne Eintrag: {l} liest {z['datei']}")
            for l in sorted(soll - ist):
                befunde.append(f"Eintrag ohne Leser: {l} nennt {z['datei']} nicht")
        if z["ablauf"] == "unbekannt":
            befunde.append(f"Ablauf unbekannt: {z['zugang']}")
            continue
        datum = z["rotation"] if z["ablauf"] == "keiner" else z["ablauf"]
        if datum == "-":
            if z["art"] == "datei":
                befunde.append(f"Schluessel ohne Ablauf und ohne Rotationsdatum: {z['zugang']}")
            continue
        rest = (datetime.date.fromisoformat(datum) - heute).days
        if rest < 0:
            befunde.append(f"Ablauf vorbei: {z['zugang']} seit {-rest} Tagen")
        elif rest <= tage:
            befunde.append(f"Ablauf nah: {z['zugang']} in {rest} Tagen")
        if naechster is None or rest < naechster[0]:
            naechster = (rest, z["zugang"])
    return register, befunde, naechster


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tage", type=int, default=60); ap.add_argument("--bericht", action="store_true")
    a = ap.parse_args()
    register, befunde, naechster = pruefen(a.tage)
    if a.bericht:
        n = f", naechster Ablauf in {naechster[0]} Tagen ({naechster[1]})" if naechster else ""
        print(f"Zugaenge: {len(register)} gefuehrt, {len(befunde)} Befunde{n}")
    else:
        for b in befunde:
            print("BEFUND " + b)
        print(f"{len(register)} Zugaenge, {len(befunde)} Befunde")
    sys.exit(77 if befunde else 0)
