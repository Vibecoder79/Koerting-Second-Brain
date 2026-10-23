#!/usr/bin/env python3
"""Prueft eine Agentenakte gegen das Schema: Felder, Werte, Abschnitte in Reihenfolge, Traeger je Grenze, Abbruchzeile, Abnahme je Version, Lebenslauf. Meldet, aendert nichts.

    agenten_wache.py <akte.md> [<akte.md> ...]

Schema: agenten-schema.tsv, Traeger: traeger.tsv, beide neben diesem Skript (AGENTEN_SCHEMA_DIR).
Rueckgabe 0 ohne Befund, 77 mit Befund. Die Wache prueft, ob jede Frage beantwortet ist; ob die
Antwort taugt, ist ein Urteil und bleibt beim Eigner.
"""
import csv
import os
import pathlib
import re
import sys

HIER = pathlib.Path(os.environ.get("AGENTEN_SCHEMA_DIR", pathlib.Path(__file__).resolve().parent))
ANGABEN = ("Lauf", "Externes Signal", "Bewertbar", "Was sich ändern darf", "Wer freigibt", "Rückführung", "Nachweis")


def tsv(name):
    with (HIER / name).open(encoding="utf-8") as f:
        return list(csv.DictReader((z for z in f if not z.startswith("#")), delimiter="\t"))


def lesen(pfad):
    text = pathlib.Path(pfad).read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text:
        return None, None
    kopf, rumpf = text[4:].split("\n---\n", 1)
    felder = {}
    for z in kopf.splitlines():
        if ":" in z and not z.startswith((" ", "#")):
            k, v = z.split(":", 1)
            felder[k.strip()] = v.strip().strip('"')
    abschnitte, aktuell = {}, None
    for z in rumpf.splitlines():
        if z.startswith("## "):
            aktuell = re.split(r"\s+[—-]\s+", z[3:].strip(), 1)[0] if not z[3:].startswith("Aufgaben") else "Aufgaben — die Stelle"
            abschnitte[aktuell] = []
        elif aktuell:
            abschnitte[aktuell].append(z)
    return felder, abschnitte


def pruefen(pfad):
    felder, abschnitte = lesen(pfad)
    if felder is None:
        return ["kein Datenkopf"]
    b = []
    schema, traeger = tsv("agenten-schema.tsv"), {t["name"]: t["stand"] for t in tsv("traeger.tsv")}
    aussen = "rufname" in felder
    for s in [s for s in schema if s["art"] == "feld"]:
        wert = felder.get(s["name"])
        noetig = s["pflicht"] == "alle" or (s["pflicht"] == "aussenkontakt" and aussen)
        if noetig and not wert:
            b.append(f"Feld fehlt: {s['name']}")
        if wert and s["werte"] and wert not in s["werte"].split("|"):
            b.append(f"Feld {s['name']}: «{wert}» ist kein erlaubter Wert ({s['werte']})")
    if felder.get("version") and not re.fullmatch(r"[1-9][0-9]*", felder["version"]):
        b.append("Feld version: keine Ganzzahl")
    # Abschnitte: vorhanden und in der Soll-Reihenfolge
    soll = [s["name"] for s in schema if s["art"] == "abschnitt" and (s["pflicht"] == "alle" or aussen)]
    for name in soll:
        if name not in abschnitte:
            b.append(f"Abschnitt fehlt: {name}")
    ist = [n for n in abschnitte if n in soll]
    if ist != [n for n in soll if n in abschnitte]:
        b.append("Abschnitte nicht in der Soll-Reihenfolge")
    # Grenzen: Traeger je Zeile, Abbruch
    genannt, geplant = set(), set()
    grenzen = [z for z in abschnitte.get("Grenzen", []) if z.startswith("- ")]
    for z in grenzen:
        m = re.search(r"Träger:\s*(.+?)\s*$", z)
        if not m:
            b.append(f"Grenze ohne Träger: {z[2:60]}"); continue
        if m.group(1).startswith("Prosa"):
            if not re.match(r"Prosa, weil \S", m.group(1)):
                b.append(f"Prosa ohne Grund: {z[2:60]}")
            continue
        for name in [n.strip() for n in m.group(1).split(",")]:
            genannt.add(name)
            if name not in traeger:
                b.append(f"Träger unbekannt: {name}")
            elif traeger[name] == "geplant":
                geplant.add(name)
    if "Grenzen" in abschnitte and not any(re.match(r"-\s*\**Abbruch:", z) for z in grenzen):
        b.append("Grenzen: keine Zeile beginnt mit Abbruch:")
    # Abnahme: nur je Version, nur mit gebauten Traegern
    if felder.get("abgenommen"):
        m = re.fullmatch(r"\d{4}-\d{2}-\d{2} v(\d+)", felder["abgenommen"])
        if not m:
            b.append("abgenommen: Form ist YYYY-MM-DD vN")
        elif m.group(1) != felder.get("version"):
            b.append(f"abgenommen gilt v{m.group(1)}, die Akte ist v{felder.get('version')}: neu abnehmen")
        if geplant:
            b.append(f"abgenommen, obwohl Träger nur geplant: {', '.join(sorted(geplant))}")
    # Lebenslauf
    status = felder.get("status", "aktiv")
    if status != "aktiv":
        for f in ("status_grund", "status_seit"):
            if not felder.get(f):
                b.append(f"status {status} ohne {f}")
    # Stil bei Aussenkontakt: beide Sprachen
    if aussen and "Stil" in abschnitte:
        text = "\n".join(abschnitte["Stil"]).lower()
        if not (re.search(r"\bde\b|deutsch", text) and re.search(r"\ben\b|englisch|english", text)):
            b.append("Stil nennt bei Aussenkontakt nicht beide Sprachen (Marker de und en)")
    # Sieben Angaben
    if "Wie dieser Agent besser wird" in abschnitte:
        text = "\n".join(abschnitte["Wie dieser Agent besser wird"])
        for a in ANGABEN:
            if not re.search(rf"\*\*{re.escape(a)}:\*\*[ \t]*\S", text):   # nur dieselbe Zeile, nicht die naechste
                b.append(f"Besser werden: Angabe «{a}» fehlt oder ist leer")
    return b


if __name__ == "__main__":
    rot = 0
    for pfad in sys.argv[1:] or sys.exit(__doc__):
        befunde = pruefen(pfad)
        print(f"== {pathlib.Path(pfad).name}: {len(befunde)} Befunde")
        for x in befunde:
            print("  BEFUND " + x)
        rot += bool(befunde)
    sys.exit(77 if rot else 0)
