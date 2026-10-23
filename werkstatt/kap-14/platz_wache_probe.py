#!/usr/bin/env python3
"""Probe der Platz-Wache: kein loeschender Aufruf im Code, und die Stufen bei 50, 85 und 95 Prozent. Dazu eine Gegenprobe, die den Scanner selbst prueft.

    platz_wache_probe.py

Der Scanner kennt die loeschenden Namen der Standardbibliothek (als Methode oder importierter Name) und
rm, rmdir, unlink, -delete in Zeichenketten unter 200 Zeichen (Docstrings sind laenger). Was er nicht kennt,
etwa ein selbst geschriebenes Loeschen ueber einen Dateideskriptor oder einen Befehl in einer langen
Zeichenkette, faengt er nicht; die Liste ist deshalb bewusst kurz und steht hier.
"""
import ast
import importlib.util
import re
import pathlib
import sys
import tempfile

HIER = pathlib.Path(__file__).resolve().parent
VERBOTEN = {"remove", "unlink", "rmdir", "removedirs", "rmtree", "move", "replace", "rename"}


BEFEHLE = re.compile(r"(^|[\s;&|])(rm|rmdir|unlink)\b|-delete\b")


def loeschende_aufrufe(quelle):
    """Jeder Aufruf, dessen Name auf der Liste steht, als Methode oder als importierter Name, und jede
    Zeichenkette mit einem Loeschbefehl; ein Docstring, der «loescht nie» sagt, zaehlt nicht."""
    baum = ast.parse(quelle)
    treffer = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.Call):
            name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id if isinstance(n.func, ast.Name) else ""
            if name in VERBOTEN:
                treffer.add(name)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 200:   # Docstrings sind laenger
            if BEFEHLE.search(n.value):
                treffer.add("befehl: " + n.value[:30])
    return sorted(treffer)


def laden(pfad):
    spec = importlib.util.spec_from_file_location("platz_wache", pfad)
    modul = importlib.util.module_from_spec(spec); spec.loader.exec_module(modul)
    return modul


rot = 0
quelle = (HIER / "platz_wache.py").read_text(encoding="utf-8")
treffer = loeschende_aufrufe(quelle)
print(f"loeschende Aufrufe in platz_wache.py: {treffer or 'keine'}"); rot += bool(treffer)
for variante in ("import shutil\nshutil.rmtree('/nirgends')", "from shutil import rmtree\nrmtree('/nirgends')",
                 "import subprocess\nsubprocess.run('rm -rf /nirgends', shell=True)", "import subprocess\nsubprocess.run(['find', '/nirgends', '-delete'])"):
    gegen = loeschende_aufrufe(quelle + "\n" + variante + "\n")
    print(f"Gegenprobe «{variante.splitlines()[-1][:40]}»: {'erkannt' if gegen else 'NICHT erkannt'}"); rot += not gegen
w = laden(HIER / "platz_wache.py")
for prozent, soll in ((50, "OK"), (85, "HINWEIS"), (95, "ALARM")):
    stufe, rc, _ = w.bewerten({"prozent": prozent, "frei_gb": 1.0}, [], [])
    ok = stufe == soll and rc == (0 if soll == "OK" else 77)
    print(f"{prozent} %: {stufe}, rc {rc}: {'OK' if ok else 'FEHLER'}"); rot += not ok
with tempfile.TemporaryDirectory() as d:
    alt = pathlib.Path(d, "alt"); alt.mkdir(); (alt / "x").write_text("x")
    import os; os.utime(alt / "x", (0, 0)); os.utime(alt, (0, 0))
    neu = pathlib.Path(d, "neu"); neu.mkdir(); (neu / "y").write_text("y")
    gefunden = [p for p, _ in w.altstaende(pathlib.Path(d), __import__("time").time())]
    ok = gefunden == [str(alt)]
    print(f"Altstand: {[pathlib.Path(p).name for p in gefunden]}: {'OK' if ok else 'FEHLER'}"); rot += not ok
sys.exit(1 if rot else 0)
