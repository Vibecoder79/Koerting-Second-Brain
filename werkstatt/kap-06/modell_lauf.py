#!/usr/bin/env python3
"""Die Huelle um einen Modellaufruf aus einem Job: festes Modell, gesperrte Werkzeuge, vier Pruefstufen.

    modell_lauf.py --job steckbrief --eingabe dokument.txt --ausgabe steckbrief.md
Rueckgabe 0 gelungen, 69 voruebergehend (naechster Lauf), 77 dauerhaft (ein neuer Versuch hilft nie).
Ein Rueckgabewert 0 von `claude -p` heisst nichts: gezaehlt werden die Zuege (num_turns), die
Arbeitsschritte des Modells. 69 statt 75 wie bei der Sperre: Dort ist etwas belegt, hier nicht erreichbar.
"""
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys

import modellwahl

VORUEBERGEHEND, DAUERHAFT = 69, 77


def auswerten(ausgabe):
    """Stufe 2 bis 4: lesbar, mindestens ein Zug, kein Fehlerkennzeichen, Ergebnis nicht leer."""
    try:
        d = json.loads(ausgabe)
    except ValueError:
        return VORUEBERGEHEND, "Antwort ist kein JSON (abgeschnitten?)", None
    zuege = d.get("num_turns") or 0
    if zuege < 1:
        return DAUERHAFT, f"num_turns={zuege}: es lief kein Modell; gibt es den Aufruf so?", d
    if d.get("is_error") or not (d.get("result") or "").strip():
        return DAUERHAFT, f"is_error={d.get('is_error')}, Ergebnis leer", d
    return 0, "", d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--eingabe", required=True)
    ap.add_argument("--ausgabe", required=True)
    a = ap.parse_args()
    material = pathlib.Path(a.eingabe).read_text(encoding="utf-8")
    prompt = ("Fasse das folgende Dokument in hoechstens drei Saetzen zusammen. "
              "Antworte nur mit der Zusammenfassung.\n\n" + material)   # Kapitel 8 legt hier den Zaun um das Material
    befehl = modellwahl.kommando(a.job)
    pathlib.Path(a.ausgabe).parent.mkdir(parents=True, exist_ok=True)   # vor dem bezahlten Aufruf, nicht danach
    umgebung = dict(os.environ)
    umgebung.pop("CLAUDECODE", None)                 # aus einer Sitzung heraus gestartet: kein verschachtelter Modus
    attrappe = os.environ.get("MODELL_LAUF_ATTRAPPE")  # fuer die Probe: eine aufgezeichnete Antwort statt eines Aufrufs
    try:
        if attrappe:
            stdout, rc, fehler = pathlib.Path(attrappe).read_text(encoding="utf-8"), 0, ""
        else:
            lauf = subprocess.run(befehl, input=prompt, capture_output=True, text=True,
                                  timeout=180, env=umgebung)
            stdout, rc, fehler = lauf.stdout, lauf.returncode, lauf.stderr
    except FileNotFoundError:
        print("DAUERHAFT: claude nicht im PATH; laeuft der Job unter dem Konto mit der Kommandozeile?", file=sys.stderr)
        sys.exit(DAUERHAFT)
    except subprocess.TimeoutExpired:
        print("VORUEBERGEHEND: Zeitgrenze von 180 s ueberschritten", file=sys.stderr)
        sys.exit(VORUEBERGEHEND)
    if rc != 0:                                        # Stufe 1: Prozess nicht sauber beendet; der Grund steht auf stderr
        print(f"VORUEBERGEHEND: Prozess endete mit {rc}: {fehler.strip()[-300:]}", file=sys.stderr); sys.exit(VORUEBERGEHEND)
    klasse, grund, d = auswerten(stdout)
    if klasse:
        print(("DAUERHAFT: " if klasse == DAUERHAFT else "VORUEBERGEHEND: ") + grund, file=sys.stderr)
        sys.exit(klasse)
    modelle = ",".join(sorted((d.get("modelUsage") or {}).keys())) or "unbekannt"
    kopf = (f"---\ntyp: steckbrief\nsource: job-{a.job}\nprovenance:\n  origin: ai-claude\n"
            f"job: {a.job}\nmodell: {modelle}\nkosten_usd: {d.get('total_cost_usd')}\n"
            f"erstellt: {datetime.date.today().isoformat()}\n---\n")
    pathlib.Path(a.ausgabe).write_text(kopf + d["result"].strip() + "\n", encoding="utf-8")
    print(f"OK: {a.ausgabe}, {d.get('num_turns')} Zug/Zuege, Modell {modelle}")


if __name__ == "__main__":
    main()
