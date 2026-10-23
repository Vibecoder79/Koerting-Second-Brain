#!/usr/bin/env python3
"""Eine Mail als ENTWURF im Postfach anlegen und den Entwurf nachlesen; gesendet wird vom Eigner.

    mail_entwurf.py --an "Muster Anna" --betreff "…" --text "…" [--ausfuehren]
Der Empfaenger kommt aus einer Kontakt-Notiz (Feld mail:) oder als Adresse vom Eigner.
Erfolg heisst: der Entwurf liegt und wurde mit einem zweiten Aufruf zurueckgelesen.
Rueckgabe 0, 77 dauerhaft (auch: Rueckpruefung gescheitert; ein Wiederholen legte einen zweiten an).
"""
import argparse
import os
import pathlib
import re
import sys

import graph

VAULT = pathlib.Path(os.environ.get("VAULT_DIR", "/opt/vault/work/vault"))
POSTFACH = os.environ.get("MAIL_POSTFACH", "eigner@example.org")


def adresse(an):
    if "@" in an:
        return an                                            # vom Eigner genannt
    treffer = []
    for p in VAULT.rglob("*.md"):
        kopf = p.read_text(encoding="utf-8")[:1500]
        if "typ: kontakt" in kopf and all(w.lower() in p.stem.lower() for w in an.split()):
            m = re.search(r"^mail:\s*(\S+@\S+)", kopf, re.M)
            if m:
                treffer.append((p.stem, m.group(1)))
    if len(treffer) != 1:
        print(f"Empfaenger «{an}»: {len(treffer)} Treffer in den Kontakt-Notizen {treffer}; kein Entwurf an den Falschen", file=sys.stderr)
        sys.exit(77)
    return treffer[0][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--an", required=True); ap.add_argument("--betreff", required=True)
    ap.add_argument("--text", required=True); ap.add_argument("--ausfuehren", action="store_true")
    a = ap.parse_args()
    an = adresse(a.an)
    rumpf = {"subject": a.betreff, "body": {"contentType": "Text", "content": a.text},
             "toRecipients": [{"emailAddress": {"address": an}}]}
    print(f"{'ENTWURF' if a.ausfuehren else 'TROCKEN'}: an {an}, Betreff «{a.betreff}», Postfach {POSTFACH}")
    if not a.ausfuehren:
        return
    tok = graph.token()
    antwort = graph.aufruf(tok, "POST", f"/users/{POSTFACH}/messages", rumpf)
    kennung = antwort.get("id")
    if not kennung:
        print("77 Antwort ohne Kennung: kein Beleg, dass der Entwurf liegt"); sys.exit(77)
    try:
        zurueck = graph.aufruf(tok, "GET", f"/users/{POSTFACH}/messages/{kennung}")  # Rueckpruefung im Zielsystem
    except SystemExit as f:                              # der Entwurf kann schon liegen: nie wiederholen
        print(f"77 Rueckpruefung nicht moeglich (Klasse {f.code}); Entwurf {kennung} kann schon liegen, nicht wiederholen"); sys.exit(77)
    ist_an = {r["emailAddress"]["address"].lower() for r in zurueck.get("toRecipients", [])}
    if not zurueck.get("isDraft") or zurueck.get("subject") != a.betreff or ist_an != {an.lower()}:
        print(f"77 Rueckpruefung gescheitert: isDraft={zurueck.get('isDraft')}, an={ist_an}"); sys.exit(77)
    print(f"Rueckpruefung: ok, Entwurf {kennung} liegt im Postfach, an {an}")


if __name__ == "__main__":
    main()
