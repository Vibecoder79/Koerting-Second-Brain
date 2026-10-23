#!/usr/bin/env python3
"""Pruefstand fuer die Abnahme einer Stelle: Faelle als Dateien, Negativfall mit Gegenprobe, dreimal bestanden, Ergebnis an die Version gebunden.

    abnahme_pruefen.py --akte <akte.md> --faelle <ordner> --stelle "<befehl>"      Faelle fahren
    abnahme_pruefen.py --akte <akte.md> --faelle <ordner> --stand                   gilt die Abnahme fuer diese Version?

Die Stelle ist ein Befehl, der die Eingabe auf stdin bekommt und JSON {antwort, auftraege} liefert;
hier die Attrappe, im Betrieb der Aufruf des Modells mit Identitaet, Zaun und Wegwerf-Ausfuehrer.
Pruefungen: enthaelt, enthaelt_nicht, regex, keine_auftraege, auftrag (aktion). Ein Lauf ohne Ausgabe
oder mit Rueckgabe ungleich 0 ist rot, sonst bestuende ein toter Modellaufruf jeden Negativfall.
Das Ergebnis steht in <ordner>/ergebnis.json mit Version und Pruefsumme der Akte; eine Akte mit
anderer Version oder anderem Text (auch nur ein geaendertes model) hat keine Abnahme. Die Felder,
die der Eigner nach dem Lauf setzt (abgenommen, status), zaehlen nicht zur Pruefsumme.
Rueckgabe 0 alles bestanden, 1 ein Fall rot, 2 der Satz der Faelle ist unvollstaendig.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

WIEDERHOLUNGEN = {"positiv": 1, "negativ": 3, "gegenprobe": 3}


EIGNER_FELDER = re.compile(r"^(abgenommen|status|status_grund|status_seit):.*\n", re.M)


def version_der_akte(pfad):
    """Version und Pruefsumme der Akte. Die Felder, die nur der Eigner setzt, bleiben aussen vor:
    Sonst veraltete die Abnahme in dem Moment, in dem der Eigner sie eintraegt."""
    text = pathlib.Path(pfad).read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\d+)\s*$", text, re.M)
    return (m.group(1) if m else None), hashlib.sha256(EIGNER_FELDER.sub("", text).encode()).hexdigest()[:12]


def faelle_lesen(ordner):
    faelle = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pathlib.Path(ordner).glob("*.json")) if p.name != "ergebnis.json"]
    maengel = []
    if sum(f.get("art") == "positiv" for f in faelle) < 2:
        maengel.append("weniger als zwei Positivfaelle")
    negativ = [f.get("id", "?") for f in faelle if f.get("art") == "negativ"]
    if not negativ:
        maengel.append("kein Negativfall")
    for n in negativ:
        if not any(f.get("art") == "gegenprobe" and f.get("gegenprobe_zu") == n for f in faelle):
            maengel.append(f"Negativfall {n} ohne Gegenprobe: eine Stelle, die alles ablehnt, bestuende ihn auch")
    for f in faelle:
        for feld in ("id", "art", "ausloeser", "eingabe", "erwartet", "fehlschlag_erkennbar_an", "pruefungen"):
            if feld not in f:
                maengel.append(f"Fall {f.get('id', '?')}: Feld {feld} fehlt")
        if f.get("art") not in WIEDERHOLUNGEN:
            maengel.append(f"Fall {f.get('id', '?')}: art muss positiv, negativ oder gegenprobe sein")
        if any("typ" not in p for p in f.get("pruefungen", [])):
            maengel.append(f"Fall {f.get('id', '?')}: eine Pruefung ohne typ")
    return faelle, maengel


def pruefung(p, ergebnis):
    antwort, auftraege = ergebnis.get("antwort", ""), ergebnis.get("auftraege", [])
    if p["typ"] == "enthaelt":
        return p["wert"].lower() in antwort.lower()
    if p["typ"] == "enthaelt_nicht":
        return p["wert"].lower() not in antwort.lower()
    if p["typ"] == "regex":
        return re.search(p["wert"], antwort) is not None
    if p["typ"] == "keine_auftraege":
        return not auftraege
    if p["typ"] == "auftrag":
        return any(a.get("aktion") == p["wert"] for a in auftraege)
    raise SystemExit(f"ABBRUCH: unbekannte Pruefung {p['typ']}")


def fahren(faelle, stelle):
    rot = 0
    for f in faelle:
        for runde in range(1, WIEDERHOLUNGEN[f["art"]] + 1):
            try:
                lauf = subprocess.run(stelle, shell=True, input=f["eingabe"], capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                print(f"  ROT   {f['id']} ({f['art']}, Lauf {runde}): Zeitdeckel"); rot += 1; continue
            if lauf.returncode != 0 or not lauf.stdout.strip():
                print(f"  ROT   {f['id']} ({f['art']}, Lauf {runde}): Stelle ohne Ergebnis (rc {lauf.returncode})"); rot += 1; continue
            try:
                ergebnis = json.loads(lauf.stdout)
            except ValueError:
                ergebnis = {"antwort": lauf.stdout, "auftraege": []}
            fehl = [p for p in f["pruefungen"] if not pruefung(p, ergebnis)]
            print(f"  {'ROT  ' if fehl else 'GRUEN'} {f['id']} ({f['art']}, Lauf {runde})"
                  + (": " + "; ".join(p.get("zweck", p["typ"]) for p in fehl) if fehl else ""))
            rot += bool(fehl)
    return rot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--akte", required=True); ap.add_argument("--faelle", required=True)
    ap.add_argument("--stelle"); ap.add_argument("--stand", action="store_true")
    a = ap.parse_args()
    version, summe = version_der_akte(a.akte)
    ergebnis_datei = pathlib.Path(a.faelle) / "ergebnis.json"
    if a.stand:
        e = json.loads(ergebnis_datei.read_text(encoding="utf-8")) if ergebnis_datei.exists() else None
        if not e:
            sys.exit(f"KEINE ABNAHME: kein Ergebnis fuer Akte v{version}")
        if not e["bestanden"]:
            sys.exit(f"NICHT BESTANDEN: letzter Lauf fuer v{e['version']} am {e['datum']} war rot")
        if e["version"] != version or e["summe"] != summe:
            sys.exit(f"ABNAHME VERALTET: Ergebnis gilt v{e['version']} ({e['summe']}), Akte ist v{version} ({summe})")
        print(f"ABNAHME GILT: v{version} ({summe}), {e['faelle']} Faelle am {e['datum']} bestanden"); sys.exit(0)
    faelle, maengel = faelle_lesen(a.faelle)
    for m in maengel:
        print("MANGEL " + m)
    if maengel or not a.stelle:
        sys.exit(2)
    rot = fahren(faelle, a.stelle)
    ergebnis_datei.write_text(json.dumps({"version": version, "summe": summe, "datum": datetime.date.today().isoformat(),
                                          "faelle": len(faelle), "bestanden": rot == 0}, indent=1), encoding="utf-8")
    print(f"{len(faelle)} Faelle, {rot} rote Laeufe, Ergebnis fuer Akte v{version} geschrieben")
    sys.exit(1 if rot else 0)
