#!/usr/bin/env python3
"""Datenkopf einer Notiz gegen schema.tsv pruefen und Befunde ausgeben.

Aufruf von Hand:   python3 wache.py <datei.md>
Als Hook:          python3 wache.py --hook   (liest den Hook-Eingang als JSON von stdin)
Rueckgabe immer 0: eine Wache haelt nichts an. Befunde stehen in der Ausgabe, Hinweise
(Stufe empfohlen) getrennt davon. Ein eigener Fehler erscheint als Systemmeldung.
"""
import json
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent
VAULT = HIER.parents[1]
DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def schema_lesen():
    regeln = []
    for zeile in (HIER / "schema.tsv").read_text(encoding="utf-8").splitlines():
        if not zeile.strip() or zeile.startswith("#") or zeile.startswith("sorte\t"):
            continue
        sorte, feld, pflicht, werte, _ = zeile.split("\t", 4)
        regeln.append((sorte, feld, pflicht, [] if werte == "-" else werte.split("|")))
    return regeln


def kopf_lesen(text):
    """Nur die flache Form `feld: wert`; verschachtelte Felder als a.b. Kein YAML-Modul,
    damit die Wache in jeder Umgebung laeuft, in der Python laeuft."""
    if not text.startswith("---\n"):
        return None
    ende = text.find("\n---", 4)
    if ende < 0:
        return None
    felder, eltern = {}, None
    for zeile in text[4:ende].splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)([\w.-]+):\s*(.*?)(?:\s+#.*)?$", zeile)   # Kommentar erst ab « #»
        if not m:
            continue
        einzug, feld, wert = m.group(1), m.group(2), m.group(3)
        if einzug and eltern:
            felder[f"{eltern}.{feld}"] = wert
        else:
            felder[feld] = wert
            eltern = feld if wert == "" else None
    return felder


def sorte_bestimmen(pfad, felder):
    """Die Sorte folgt aus dem Ort oder aus einem Feld; der Ort gewinnt nur, wo er eindeutig ist."""
    rel = pfad.relative_to(VAULT).as_posix()
    if felder.get("typ") == "aufgabe":
        return "aufgabe"
    if rel.startswith("01 Inbox/"):
        return "inbox"
    if rel.startswith("02 Projekte/") and pfad.name.endswith(" - Hub.md"):
        return "projekt-hub"
    return "notiz"


def pruefen(pfad):
    """(befunde, hinweise). Dateien ausserhalb des Vaults gehen die Wache nichts an."""
    if VAULT not in pfad.parents:
        return [], []
    text = pfad.read_text(encoding="utf-8")
    felder = kopf_lesen(text)
    if felder is None:
        return ["kein Datenkopf (Datei beginnt nicht mit ---)"], []
    sorte = sorte_bestimmen(pfad, felder)
    befunde, hinweise = [], []
    for s, feld, pflicht, werte in schema_lesen():
        if s not in ("*", sorte):
            continue
        wert = felder.get(feld)
        if wert is None or wert == "":
            if pflicht in ("alle", "hub"):
                befunde.append(f"{feld}: fehlt (Pflicht fuer {sorte})")
            elif pflicht == "eigner":
                befunde.append(f"{feld}: fehlt; Werte {'|'.join(werte)}. Setzt nur der Eigner, bitte fragen")
            elif pflicht == "empfohlen":
                hinweise.append(f"{feld}: fehlt (empfohlen)")
            continue
        if werte and wert not in werte:
            if "JJJJ-MM-TT" in werte and DATUM.match(wert):
                continue
            befunde.append(f"{feld}: «{wert}» ist kein erlaubter Wert ({'|'.join(werte)})")
    return befunde, hinweise


def hook():
    eingang = json.load(sys.stdin)
    pfad = eingang.get("tool_input", {}).get("file_path")
    if not pfad or not pfad.endswith(".md"):
        return
    befunde, hinweise = pruefen(pathlib.Path(pfad).resolve())
    zeilen = befunde + [f"Hinweis: {h}" for h in hinweise]
    if zeilen:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
              "additionalContext": "DATENKOPF-WACHE, bitte ergaenzen; Eigner-Felder erfragen:\n- "
              + "\n- ".join(zeilen)}}, ensure_ascii=False))


def main():
    try:
        if "--hook" in sys.argv:
            hook()
            return
        for name in sys.argv[1:]:
            befunde, hinweise = pruefen(pathlib.Path(name).resolve())
            print(f"{name}: " + ("in Ordnung" if not befunde else f"{len(befunde)} Befund(e)")
                  + (f", {len(hinweise)} Hinweis(e)" if hinweise else ""))
            for b in befunde:
                print(f"  - {b}")
            for h in hinweise:
                print(f"  - Hinweis: {h}")
    except Exception as e:   # eine Wache, die abstuerzt, schweigt; das darf sie nicht
        print(json.dumps({"systemMessage": f"DATENKOPF-WACHE: eigener Fehler, Wache fuer diesen Aufruf inaktiv: {e}"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
