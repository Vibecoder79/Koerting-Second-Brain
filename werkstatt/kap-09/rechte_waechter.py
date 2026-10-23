#!/usr/bin/env python3
"""Soll-Ist-Waechter: die Rollen im Zugangstoken gegen soll.txt, in beide Richtungen. Die Ablaufdaten prueft der Waechter des Registers der Zugaenge (Kapitel 11).

Das Token wird nie ausgegeben; Rollennamen sind Betriebsdaten.    0 Soll = Ist   77 Abweichung   78 nicht messbar
"""
import base64
import json
import os
import pathlib
import sys
import urllib.error

import graph

HIER = pathlib.Path(__file__).resolve().parent


def rollen_im_token(tok):
    nutzlast = tok.split(".")[1]
    nutzlast += "=" * (-len(nutzlast) % 4)
    return {r for r in json.loads(base64.urlsafe_b64decode(nutzlast)).get("roles", []) if r}


def main():
    try:
        soll = {z.strip() for z in (HIER / "soll.txt").read_text(encoding="utf-8").splitlines()
                if z.strip() and not z.startswith("#")}
        ist = rollen_im_token(graph.token())
    except (urllib.error.URLError, OSError, ValueError, IndexError, SystemExit) as f:
        print(f"NICHT MESSBAR: Soll oder Token fehlt ({f})"); sys.exit(78)
    rc = 0
    for r in sorted(ist - soll):
        print(f"ABWEICHUNG: Recht zu viel: {r}"); rc = 77
    for r in sorted(soll - ist):
        print(f"ABWEICHUNG: Recht fehlt, der Job scheitert still: {r}"); rc = 77
    print("OK: Rollen wie im Soll" if rc == 0 else "ROT")
    sys.exit(rc)


if __name__ == "__main__":
    main()
