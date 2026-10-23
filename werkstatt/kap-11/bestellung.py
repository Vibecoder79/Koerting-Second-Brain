#!/usr/bin/env python3
"""Bestellt bei einem bezahlten Dienst, idempotent und gedeckelt: Journal vor dem Aufruf, nie eine zweite Bestellung bei Unklarheit.

    bestellung.py bestellen --auftrag <kennung> --nr <n>     eine Bestellung; gleiche Kennung und Nummer heisst dieselbe
    bestellung.py abgleichen --schluessel <k>                 eine unklare Bestellung beim Dienst nachfragen
    bestellung.py journal                                     alle Zeilen

Der Schluessel des Dienstes liegt in BILDDIENST_ZUGANG und wird nur hier gelesen. Preis und
Deckel kommen aus bindung.json mit Preisbeleg; ohne Beleg wird nicht bestellt. Rueckgabe:
0 bestellt, schon bestellt oder abgeglichen; 69 unklar (keine oder eine 5xx-Antwort, Abgleich noetig);
77 angehalten am Deckel, vom Dienst abgewiesen (4xx) oder unklar und deshalb nicht erneut bestellt.
Jeder 2xx- oder 3xx-Code ohne das Feld job zaehlt als unklar, nicht als abgewiesen.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

JOURNAL = pathlib.Path(os.environ.get("BESTELL_JOURNAL", "/opt/vault/bestellungen.sqlite"))
ZUGANG = pathlib.Path(os.environ.get("BILDDIENST_ZUGANG", "/opt/vault/secrets/bilddienst.env"))
BINDUNG = json.loads(pathlib.Path(os.environ.get("BESTELL_BINDUNG", "bindung.json")).read_text(encoding="utf-8"))
PREIS = int(round(BINDUNG["preis_je_bild_usd"] * 1_000_000))    # Mikro-USD, kein Float im Journal
DECKEL = int(round(BINDUNG["deckel_je_auftrag_usd"] * 1_000_000))


def db():
    d = sqlite3.connect(JOURNAL, isolation_level=None); d.row_factory = sqlite3.Row
    d.execute("CREATE TABLE IF NOT EXISTS bestellungen (schluessel TEXT PRIMARY KEY, auftrag TEXT, nr INTEGER, "
              "status TEXT, preis_micro INTEGER, job TEXT, angelegt TEXT, geaendert TEXT)")
    return d


def jetzt():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def schluessel_lesen():
    """Die Zugangsdatei traegt NAME=wert je Zeile, wie in Kapitel 9; gelesen wird nur die eigene Zeile."""
    if not ZUGANG.is_file():
        sys.exit(f"ABBRUCH: Zugangsdatei {ZUGANG} fehlt oder ist nicht lesbar")
    for z in ZUGANG.read_text(encoding="utf-8").splitlines():
        if z.startswith("BILDDIENST_SCHLUESSEL="):
            return z.split("=", 1)[1].strip()
    sys.exit("ABBRUCH: BILDDIENST_SCHLUESSEL fehlt in der Zugangsdatei")


def adresse_pruefen():
    if urllib.parse.urlsplit(BINDUNG["dienst"]).hostname not in BINDUNG["erlaubte_hosts"]:
        sys.exit("ABBRUCH: Dienstadresse nicht in der Allowlist")


def dienst(methode, pfad, schluessel=None, rumpf=None):
    """Der einzige Weg zum Dienst: feste Adresse aus der Bindung, Zugang aus der Datei, kurzer Timeout."""
    adresse_pruefen()
    kopf = {"Authorization": "Bearer " + schluessel_lesen(), "Content-Type": "application/json"}
    if schluessel:
        kopf["Idempotency-Key"] = schluessel
    bitte = urllib.request.Request(BINDUNG["dienst"] + pfad, method=methode, headers=kopf,
                                   data=json.dumps(rumpf).encode() if rumpf else None)
    try:
        with urllib.request.urlopen(bitte, timeout=3) as antwort:
            return antwort.status, json.loads(antwort.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError, ValueError):
        return None, None                                        # keine oder keine lesbare Antwort: unklar, nicht «fehlgeschlagen»


def bestellen(auftrag, nr):
    if not BINDUNG.get("preisbeleg"):
        sys.exit("ABBRUCH: kein Preisbeleg in der Bindung")
    adresse_pruefen(); schluessel_lesen()                       # Vorbedingungen vor der Reservation
    schluessel = hashlib.sha256(f"{auftrag}\n{nr}".encode()).hexdigest()[:16]
    d = db()
    d.execute("BEGIN IMMEDIATE")                                 # ein Schreiber, die Zeile vor dem Aufruf
    alt = d.execute("SELECT * FROM bestellungen WHERE schluessel=?", (schluessel,)).fetchone()
    if alt and alt["status"] == "bestellt":
        d.execute("COMMIT"); print(f"SCHON BESTELLT {schluessel}: Job {alt['job']}"); return 0
    if alt and alt["status"] in ("unklar", "reserviert"):       # reserviert: ein Lauf brach nach dem Journal ab
        d.execute("COMMIT"); print(f"{alt['status'].upper()} {schluessel}: nicht erneut bestellt; abgleichen"); return 77
    offen = d.execute("SELECT COALESCE(SUM(preis_micro),0) FROM bestellungen WHERE auftrag=? AND status IN "
                      "('reserviert','bestellt','unklar')", (auftrag,)).fetchone()[0]
    if offen + PREIS > DECKEL:
        d.execute("INSERT OR REPLACE INTO bestellungen VALUES (?,?,?,?,?,?,?,?)",
                  (schluessel, auftrag, nr, "angehalten", 0, None, jetzt(), jetzt()))
        d.execute("COMMIT")
        print(f"ANGEHALTEN {schluessel}: Auftrag {auftrag} bei USD {offen / 1e6:.2f} von {DECKEL / 1e6:.2f}; Freigabe noetig")
        return 77
    d.execute("INSERT OR REPLACE INTO bestellungen VALUES (?,?,?,?,?,?,?,?)",
              (schluessel, auftrag, nr, "reserviert", PREIS, None, jetzt(), jetzt()))
    d.execute("COMMIT")
    status, antwort = dienst("POST", "/bestellungen", schluessel, {"auftrag": auftrag, "nr": nr})
    if status and 200 <= status < 300 and isinstance(antwort, dict) and "job" in antwort:
        d.execute("UPDATE bestellungen SET status='bestellt', job=?, geaendert=? WHERE schluessel=?",
                  (antwort["job"], jetzt(), schluessel))
        print(f"BESTELLT {schluessel}: Job {antwort['job']}"); return 0
    if status is None or status >= 500 or 200 <= status < 400:   # keine, eine kaputte oder eine Proxy-Antwort: angekommen oder nicht?
        d.execute("UPDATE bestellungen SET status='unklar', geaendert=? WHERE schluessel=?", (jetzt(), schluessel))
        print(f"UNKLAR {schluessel}: {'keine Antwort' if status is None else status}; Journal haelt die Reservation, abgleichen statt neu bestellen"); return 69
    d.execute("UPDATE bestellungen SET status='abgewiesen', preis_micro=0, geaendert=? WHERE schluessel=?",
              (jetzt(), schluessel))
    print(f"ABGEWIESEN {schluessel}: Dienst antwortet {status}"); return 77


def abgleichen(schluessel):
    d = db()
    zeile = d.execute("SELECT * FROM bestellungen WHERE schluessel=?", (schluessel,)).fetchone()
    if not zeile or zeile["status"] not in ("unklar", "reserviert"):
        sys.exit(f"ABBRUCH: {schluessel} ist weder unklar noch reserviert")
    status, antwort = dienst("GET", f"/bestellungen/{schluessel}")
    if status == 200 and isinstance(antwort, dict) and "job" in antwort:
        d.execute("UPDATE bestellungen SET status='bestellt', job=?, geaendert=? WHERE schluessel=?",
                  (antwort["job"], jetzt(), schluessel))
        print(f"ABGEGLICHEN {schluessel}: war angekommen, Job {antwort['job']}"); return 0
    if status == 404:
        d.execute("UPDATE bestellungen SET status='nicht-angekommen', preis_micro=0, geaendert=? WHERE schluessel=?",
                  (jetzt(), schluessel))
        print(f"ABGEGLICHEN {schluessel}: nie angekommen, Reservation freigegeben; neu bestellen ist jetzt erlaubt"); return 0
    print(f"UNKLAR {schluessel}: Dienst antwortet {status}, spaeter erneut"); return 69


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="befehl", required=True)
    b = sub.add_parser("bestellen"); b.add_argument("--auftrag", required=True); b.add_argument("--nr", type=int, required=True)
    g = sub.add_parser("abgleichen"); g.add_argument("--schluessel", required=True)
    sub.add_parser("journal")
    a = ap.parse_args()
    if a.befehl == "bestellen":
        sys.exit(bestellen(a.auftrag, a.nr))
    if a.befehl == "abgleichen":
        sys.exit(abgleichen(a.schluessel))
    for z in db().execute("SELECT schluessel, auftrag, nr, status, preis_micro, job FROM bestellungen ORDER BY angelegt"):
        print(f"{z['schluessel']}  {z['auftrag']} #{z['nr']}  {z['status']:16} USD {z['preis_micro'] / 1e6:.2f}  {z['job'] or '-'}")
