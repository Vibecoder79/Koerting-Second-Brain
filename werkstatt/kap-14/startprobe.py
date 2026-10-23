#!/usr/bin/env python3
"""Startprobe nach einem Neustart: loest jeden wichtigen Dienst aktiv aus und kennt drei Ergebnisse. Ungeprueft zaehlt nie als gruen.

    startprobe.py [startprobe.tsv]

Zeilen: name, art (befehl | datei | port), ziel, soll. Ein Port wird auf der eigenen Maschine geprueft
(127.0.0.1); ob die Firewall ihn nach aussen schliesst, misst nur eine zweite Maschine. Bei art port heisst soll «offen» oder «zu»;
«zu» braucht eine Referenz in der Spalte soll (zu,referenz=<port>), die offen sein muss, sonst
beweist das Nein nichts und die Zeile ist UNGEPRUEFT.
Rueckgabe 0 alles OK, 77 mindestens ein FEHLER, 78 nichts falsch, aber etwas UNGEPRUEFT.
"""
import csv
import os
import pathlib
import shutil
import socket
import subprocess
import sys


def port_offen(port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", int(port))) == 0


def pruefen(z):
    if z["art"] == "befehl":
        if not shutil.which(z["ziel"].split()[0]):
            return "UNGEPRUEFT", "Programm nicht vorhanden"
        try:
            r = subprocess.run(z["ziel"], shell=True, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return "UNGEPRUEFT", "keine Antwort in 30 Sekunden"
        return ("OK" if r.returncode == 0 else "FEHLER"), (r.stderr.strip() or r.stdout.strip())[:80]
    if z["art"] == "datei":
        return ("OK" if pathlib.Path(z["ziel"]).exists() else "FEHLER"), z["ziel"]
    if z["art"] == "port":
        soll, _, ref = z["soll"].partition(",")
        if soll == "offen":
            return ("OK" if port_offen(z["ziel"]) else "FEHLER"), f"Port {z['ziel']}"
        if not ref.startswith("referenz="):
            return "UNGEPRUEFT", "Abwesenheit ohne Referenz beweist nichts"
        if not port_offen(ref.split("=")[1]):
            return "UNGEPRUEFT", f"Referenzport {ref.split('=')[1]} antwortet nicht; der Prueftest selbst ist fraglich"
        return ("OK" if not port_offen(z["ziel"]) else "FEHLER"), f"Port {z['ziel']} zu, Referenz offen"
    return "UNGEPRUEFT", f"unbekannte Art {z['art']}"


pfad = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "startprobe.tsv")
with pfad.open(encoding="utf-8") as f:
    zeilen = list(csv.DictReader((z for z in f if not z.startswith("#")), delimiter="\t"))
os.environ.setdefault("VAULT_BASIS", "/opt/vault")
for z in zeilen:
    z["ziel"] = os.path.expandvars(z["ziel"])          # ${VAULT_BASIS} in der Tabelle
ergebnisse = {}
for z in zeilen:
    stand, hinweis = pruefen(z)
    ergebnisse[stand] = ergebnisse.get(stand, 0) + 1
    print(f"{stand:10} {z['name']}: {hinweis}")
print(f"{ergebnisse.get('OK', 0)} OK, {ergebnisse.get('FEHLER', 0)} FEHLER, {ergebnisse.get('UNGEPRUEFT', 0)} UNGEPRUEFT")
sys.exit(77 if ergebnisse.get("FEHLER") else 78 if ergebnisse.get("UNGEPRUEFT") else 0)
