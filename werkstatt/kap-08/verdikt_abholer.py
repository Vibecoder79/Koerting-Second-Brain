#!/usr/bin/env python3
"""Verdikte aus der Liste abholen und einloesen: erst ausfuehren, dann quittieren. Laeuft alle fuenf Minuten.

Gelesen wird nur, was noch wartet (verarbeitet=nein); «offen» ist der Normalfall. Ein Uebernehmen
schreibt den Entscheid ins Vault, mit der Kennung in Dateiname und Commit-Nachricht, und pusht; ein
Commit, der nur lokal liegt, blockierte den naechsten Push eines Klons. Eine Karte ohne Antwort
verfaellt nach 14 Tagen. Die Verdikte heissen wie auf der Karte: uebernehmen, verwerfen, ueberarbeiten.
"""
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

from freigabe_karte import LISTE, VAULT, bereinigt, liste_lesen, liste_schreiben, register

VERFALL_TAGE = 14


NACHRICHT = "feat(freigabe): {} eingeloest"


class Liegenlassen(Exception):
    """Diese Zeile bleibt liegen; der Lauf geht mit der naechsten weiter."""


def committet(kennung):
    """Steht ein Commit mit dieser Kennung in der Historie? Die Datei allein beweist nichts."""
    return bool(subprocess.run(["git", "-C", str(VAULT), "log", "--format=%h", "--fixed-strings",
                                "--grep", NACHRICHT.format(kennung)], capture_output=True, text=True).stdout.strip())


def entscheid_schreiben(z):
    """Ziel aus dem Register ueber das Kuerzel, Dateiname bereinigt: nichts davon aus freiem Text."""
    reg = register()
    if z["kuerzel"] not in reg:
        raise Liegenlassen(f"{z['kennung']}: Kuerzel {z['kuerzel']} nicht mehr vergeben; bleibt liegen")
    ordner = VAULT / reg[z["kuerzel"]] / "Decisions"
    ziel = (ordner / f"{z['angelegt_am']} {bereinigt(z['kennung'])} {bereinigt(z['titel'])}.md").resolve()
    if not str(ziel).startswith(str(ordner.resolve()) + "/"):         # Ziel bleibt im Ordner Decisions; kein assert, das faellt unter -O weg
        raise Liegenlassen(f"{z['kennung']}: Zielpfad verlaesst Decisions")
    zeile = re.compile(rf"^kennung: {re.escape(z['kennung'])}$", re.M)  # ganze Zeile: -1 trifft nicht -12
    vorhanden = next((p for p in ordner.glob("*.md") if zeile.search(p.read_text(encoding="utf-8")[:500])), None)
    if vorhanden is None:
        ordner.mkdir(parents=True, exist_ok=True)
        ziel.write_text(f"---\ntyp: entscheid\nkennung: {z['kennung']}\nstatus: entschieden\n"
                        f"entschieden_am: {z['entschieden_am']}\nsource: freigabe\n---\n# {z['titel']}\n\n"
                        f"{z['karte_text']}\n\nFreigegeben ueber die Karte {z['kennung']}.\n", encoding="utf-8")
        vorhanden = ziel
    if committet(z["kennung"]):
        return vorhanden, False
    rel = str(vorhanden.relative_to(VAULT))                              # Datei lag, Commit fehlte: nachholen
    subprocess.run(["git", "-C", str(VAULT), "add", "--", rel], check=True)
    subprocess.run(["git", "-C", str(VAULT), "commit", "-q", "-m", NACHRICHT.format(z["kennung"]), "--", rel], check=True)
    return vorhanden, True


def main():
    heute = datetime.date.today()
    zeilen = liste_lesen()
    for z in zeilen:
        if z["verarbeitet"] != "nein":
            continue
        if z["verdikt"] not in ("uebernehmen", "verwerfen"):  # offen, oder ein Wert, den diese Stufe nicht kennt
            alter = (heute - datetime.date.fromisoformat(z["angelegt_am"])).days
            if z["verdikt"] != "offen":
                print(f"{z['kennung']}: Verdikt «{z['verdikt']}» kennt diese Stufe nicht; bleibt liegen")
            if alter > VERFALL_TAGE:
                z["verarbeitet"] = "verfallen"; print(f"{z['kennung']}: ohne Antwort nach {alter} Tagen verfallen, nichts geschieht")
            continue
        if z["verdikt"] == "uebernehmen":
            try:
                ziel, neu = entscheid_schreiben(z)      # 1. ausfuehren
            except (Liegenlassen, subprocess.CalledProcessError, OSError) as f:
                print(f"{z['kennung']}: bleibt liegen ({f})"); continue   # die naechste Zeile laeuft, die Liste wird geschrieben
            print(f"{z['kennung']}: uebernommen, {'committet' if neu else 'lag schon committet'}: {ziel.name}")
        else:
            print(f"{z['kennung']}: verworfen, nichts geschieht")
        z["verarbeitet"] = "ja"                          # 2. quittieren, erst nach der Wirkung
    liste_schreiben(zeilen)
    pushen()


def pushen():
    """Die Nachernte aus Kapitel 5 pusht nur, was sie selbst committet; die Commits von hier muessen selbst hinaus."""
    if subprocess.run(["git", "-C", str(VAULT), "remote", "get-url", "origin"], capture_output=True).returncode != 0:
        return
    if subprocess.run(["git", "-C", str(VAULT), "push", "-q", "origin", "HEAD"], capture_output=True).returncode != 0:
        print("push fehlgeschlagen: Nabe und Arbeitskopie weichen ab", file=sys.stderr); sys.exit(74)


if __name__ == "__main__":
    main()
