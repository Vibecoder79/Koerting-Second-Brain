#!/usr/bin/env python3
"""Platz-Wache: Fuellstand, Zuwachs seit dem letzten Lauf und Altstaende. Meldet ab 80 Prozent, loescht nie.

    platz_wache.py              messen, Schnappschuss schreiben, Rueckgabe 0 oder 77
    platz_wache.py --bericht    eine Zeile aus dem Schnappschuss, ohne neue Messung

PLATZ_MOUNT (Standard /), PLATZ_WURZELN (mit : getrennt), PLATZ_STAND (Schnappschuss, ausserhalb
von Git). Altstand heisst: ein Eintrag unter einer Wurzel, in dem seit 14 Tagen keine Datei
geaendert wurde. «Lange nicht benutzt» heisst nicht «ueberfluessig»; entfernen tut der Mensch.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

MOUNT = os.environ.get("PLATZ_MOUNT", "/")
WURZELN = [pathlib.Path(w) for w in os.environ.get("PLATZ_WURZELN", "/opt/vault:/tmp").split(":") if w]
STAND = pathlib.Path(os.environ.get("PLATZ_STAND", "/opt/vault/heartbeats/platz-wache.json"))
HINWEIS, ALARM, ALT_TAGE, ZEITDECKEL = 80, 90, 14, 600


def belegung(mount):
    s = os.statvfs(mount)
    gesamt, frei = s.f_blocks * s.f_frsize, s.f_bavail * s.f_frsize
    return {"prozent": round(100 * (gesamt - frei) / gesamt), "frei_gb": round(frei / 1e9, 1)}


def groessen(wurzel):
    """du bis Tiefe 2, gedrosselt und mit Zeitdeckel; None heisst ungemessen."""
    try:
        r = subprocess.run(["nice", "-n", "19", "du", "-xk", "--max-depth=2", str(wurzel)],
                           capture_output=True, text=True, timeout=ZEITDECKEL)
    except subprocess.TimeoutExpired:
        return None
    return {z.split("\t", 1)[1]: int(z.split("\t", 1)[0]) for z in r.stdout.splitlines() if "\t" in z}


def altstaende(wurzel, jetzt):
    """Eintraege, in denen seit ALT_TAGE keine Datei geaendert wurde; mit demselben Zeitdeckel wie du."""
    alte, ende = [], time.time() + ZEITDECKEL
    for p in sorted(wurzel.iterdir()) if wurzel.is_dir() else []:
        try:
            juengste = p.stat().st_mtime
        except OSError:
            continue                                            # etwa ein toter Symlink
        for ordner, _, dateien in os.walk(p):
            if time.time() > ende:
                print(f"  {wurzel}: Altstaende ab {p.name} ungemessen (Zeitdeckel)", file=sys.stderr)
                return alte                                     # lieber unvollstaendig und gesagt als ein haengender Job
            for d in dateien:
                try:
                    juengste = max(juengste, os.stat(os.path.join(ordner, d)).st_mtime)
                except OSError:
                    pass
        if jetzt - juengste > ALT_TAGE * 86400:
            alte.append((str(p), round((jetzt - juengste) / 86400)))
    return alte


def bewerten(b, zuwachs, alte):
    """Die eine Stelle, die urteilt: Stufe und Rueckgabewert aus den Messwerten."""
    stufe = "ALARM" if b["prozent"] >= ALARM else "HINWEIS" if b["prozent"] >= HINWEIS else "OK"
    zeilen = [f"Platte {MOUNT}: {b['prozent']} % belegt, {b['frei_gb']} GB frei: {stufe}"]
    zeilen += [f"  Zuwachs {pfad}: +{kb // 1024} MB" for pfad, kb in zuwachs[:5]]
    zeilen += [f"  Altstand {pfad}: seit {tage} Tagen unveraendert" for pfad, tage in alte[:5]]
    return stufe, 77 if stufe != "OK" else 0, zeilen


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--bericht", action="store_true")
    a = ap.parse_args()
    if a.bericht:
        s = json.loads(STAND.read_text(encoding="utf-8")) if STAND.exists() else None
        print(f"Platte: {s['prozent']} % ({s['stufe']}), gemessen {s['datum']}" if s else "Platte: ungemessen")
        return 0 if s and s["stufe"] == "OK" else 77
    b, jetzt = belegung(MOUNT), time.time()
    vorher = json.loads(STAND.read_text(encoding="utf-8")).get("groessen", {}) if STAND.exists() else {}
    jetzt_groessen, alte = {}, []
    for w in WURZELN:
        g = groessen(w)
        if g is None:
            print(f"  {w}: ungemessen (Zeitdeckel)", file=sys.stderr); continue
        jetzt_groessen.update(g); alte += altstaende(w, jetzt)
    zuwachs = sorted(((p, kb - vorher.get(p, kb)) for p, kb in jetzt_groessen.items() if kb > vorher.get(p, kb)),
                     key=lambda x: -x[1])
    stufe, rc, zeilen = bewerten(b, zuwachs, alte)
    print("\n".join(zeilen))
    STAND.parent.mkdir(parents=True, exist_ok=True)
    STAND.write_text(json.dumps({"datum": time.strftime("%Y-%m-%d"), "prozent": b["prozent"], "stufe": stufe,
                                 "groessen": jetzt_groessen}), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
