#!/usr/bin/env python3
"""Loest fuer einen Job die Modell-Flags aus jobs.tsv und modelle.tsv auf.

    modellwahl.py --job steckbrief          die Flag-Kette fuer `claude -p`
    modellwahl.py --drift ausgabe/           Ist (modell: im Kopf jeder Ausgabe) gegen Soll
Kein Skript kennt ein Modell; ein unbekannter Job bekommt den Notnagel, mit Meldung.
"""
import argparse
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent
NOTNAGEL = ("sonnet", "medium")
RANG = {"haiku": 1, "sonnet": 2, "opus": 3}
WERKZEUGE_AUS = ["Bash", "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch", "Task"]


def tabelle(name, schluessel):
    zeilen = [z for z in (HIER / name).read_text(encoding="utf-8").splitlines()
              if z.strip() and not z.startswith("#")]
    kopf = zeilen[0].split("\t")
    return {z.split("\t")[kopf.index(schluessel)]: dict(zip(kopf, z.split("\t"))) for z in zeilen[1:]}


def aufloesen(job):
    """(stufe, effort, hinweis). Hinweis ist leer, wenn das Register den Job kennt."""
    jobs = tabelle("jobs.tsv", "name")
    stufen = tabelle("modelle.tsv", "stufe")
    eintrag = jobs.get(job)
    if not eintrag or eintrag.get("modell", "-") in ("-", ""):
        return NOTNAGEL + (f"Job «{job}» ohne Modell im Register, Notnagel {NOTNAGEL[0]}/{NOTNAGEL[1]}",)
    if eintrag["modell"] not in stufen:
        return NOTNAGEL + (f"Stufe «{eintrag['modell']}» unbekannt, Notnagel",)
    effort = eintrag.get("effort")
    return eintrag["modell"], (effort if effort not in ("-", "", None) else NOTNAGEL[1]), ""


def flags(job):
    stufe, effort, hinweis = aufloesen(job)
    if hinweis:
        print(f"modellwahl: {hinweis}", file=sys.stderr)
    stufen = tabelle("modelle.tsv", "stufe")
    kette = ["--model", stufen[stufe]["version"], "--effort", effort]
    if RANG.get(stufe, 0) > RANG["sonnet"]:           # Ersatzmodell nur oberhalb der Mitte, nie nach oben
        kette += ["--fallback-model", stufen["sonnet"]["version"]]
    return kette


def kommando(job, werkzeuge_aus=WERKZEUGE_AUS):
    """Die ganze Befehlszeile. Prompt kommt ueber stdin, nicht als Argument."""
    return (["claude", "-p", "--output-format", "json", "--strict-mcp-config",
             "--tools", "", "--disallowed-tools", *werkzeuge_aus,
             "--max-turns", "4", "--max-budget-usd", "0.5", "--no-session-persistence"]
            + flags(job))


def drift(ordner):
    """Jede Ausgabe traegt `modell:` im Kopf; das wird gegen das Soll des Jobs gehalten."""
    stufen = tabelle("modelle.tsv", "stufe")
    befunde = 0
    dateien = sorted(pathlib.Path(ordner).glob("*.md"))
    if not dateien:
        print(f"NICHT MESSBAR: keine Ausgabe in {ordner}"); return 78
    for p in dateien:
        kopf = p.read_text(encoding="utf-8")[:1500]
        job = re.search(r"^job:\s*(\S+)", kopf, re.M)
        ist = re.search(r"^modell:\s*(\S+)", kopf, re.M)
        if not job or not ist:
            print(f"ROT   {p.name}: job oder modell fehlt im Kopf"); befunde += 1; continue
        stufe, _, hinweis = aufloesen(job.group(1))
        if hinweis:                                      # ein Job ohne Registereintrag ist ein Befund, kein Notnagel
            print(f"ROT   {p.name}: {hinweis}"); befunde += 1; continue
        soll = stufen[stufe]["version"]
        # Das Werkzeug meldet alle benutzten Modelle, auch ein kleines fuer Nebenarbeit;
        # gepruefte Frage: war das Soll-Modell dabei?
        if any(m.startswith(soll) for m in ist.group(1).split(",")):
            print(f"OK    {p.name}: {ist.group(1)}")
        else:
            print(f"ROT   {p.name}: lief auf {ist.group(1)}, Soll {soll}"); befunde += 1
    return 77 if befunde else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--job")
    ap.add_argument("--drift")
    a = ap.parse_args()
    if a.drift:
        sys.exit(drift(a.drift))
    print(" ".join(kommando(a.job)))
