#!/usr/bin/env python3
"""Minimales Tagesbriefing aus Kalender und Aufgaben, ohne Sprachmodell: liest, waehlt nach festen Regeln, setzt eine Seite, sendet nur an den Eigner.

    briefing.py [--html <datei>] [--senden]

Der Kalender ist fuer die Probe eine Datei mit den Antworten des Dienstes (BRIEFING_KALENDER),
die Aufgabenliste des Dienstes ebenso (BRIEFING_AUFGABEN); eigene Aufgaben kommen aus dem Vault
(typ: aufgabe, status: offen). Zeiten kommen in Weltzeit mit Zone und werden in die Zone des
Eigners umgerechnet; eine Zeit ohne Zone bricht ab. --senden legt die Mail in den Ausgang der
Versand-Attrappe (BRIEFING_AUSGANG), und nur an den Eigner, der als Konstante im Programm steht; faellt der
Versand aus (BRIEFING_VERSAND_AUS=1), entsteht ein Entwurf (BRIEFING_ENTWUERFE) und eine
Betriebsmeldung, Rueckgabe 69. Schreibt sonst nichts.
"""
import argparse
import datetime
import html
import json
import os
import pathlib
import re
import sys
from zoneinfo import ZoneInfo

VAULT = pathlib.Path(os.environ.get("VAULT_DIR", "/opt/vault/work/vault"))
KALENDER = pathlib.Path(os.environ.get("BRIEFING_KALENDER", "/opt/vault/kalender.json"))
AUFGABEN = pathlib.Path(os.environ.get("BRIEFING_AUFGABEN", "/opt/vault/aufgaben-dienst.json"))
ZONE = ZoneInfo(os.environ.get("BRIEFING_ZEITZONE", "Europe/Zurich"))
HEUTE = datetime.date.fromisoformat(os.environ["BRIEFING_HEUTE"]) if os.environ.get("BRIEFING_HEUTE") else datetime.date.today()
EIGNER = "eigner@example.org"                                         # der einzige Empfaenger, fest im Programm
ARBEITSTAG = (8 * 60, 18 * 60)                                        # Minuten ab Mitternacht
FREIER_BLOCK_MIN = 45
FENSTER_TAGE = 7
WICHTIG = {"dringend", "wichtig"}
KLASSEN = ("ueberfaellig", "wartet", "entscheidung", "vorbereitung")  # Reihenfolge der Reihum-Auswahl
DECKEL_AUFMERKSAMKEIT = 5
KUERZEL = re.compile(r"^\s*\[([A-Z0-9-]{2,})\]")
WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def lokal(iso):
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        sys.exit(f"ABBRUCH: Zeit ohne Zone im Kalender: {iso}")
    return t.astimezone(ZONE)


def termine():
    liste = []
    for e in json.loads(KALENDER.read_text(encoding="utf-8")):
        a, b = lokal(e["start"]), lokal(e["ende"])
        if a.date() == HEUTE:
            liste.append({"betreff": e["betreff"], "von": a.hour * 60 + a.minute, "bis": b.hour * 60 + b.minute})
    return sorted(liste, key=lambda t: t["von"])


def datenkopf(p):
    t = p.read_text(encoding="utf-8", errors="replace")
    if not t.startswith("---\n"):
        return {}
    kopf = t.split("\n---", 1)[0]
    return dict((z.split(":", 1)[0].strip(), z.split(":", 1)[1].strip()) for z in kopf.splitlines() if ":" in z)


def aufgaben():
    liste = []
    for p in sorted(VAULT.rglob("*.md")):
        k = datenkopf(p)
        if k.get("typ") == "aufgabe" and k.get("status", "offen") == "offen":
            liste.append({"titel": p.stem, "faellig": k.get("faellig"), "prioritaet": k.get("prioritaet"),
                          "wartet": k.get("wartet_auf"), "art": k.get("art"), "quelle": "vault"})
    for a in json.loads(AUFGABEN.read_text(encoding="utf-8")):
        liste.append({"titel": a["titel"], "faellig": a.get("faellig"), "prioritaet": a.get("prioritaet"),
                      "wartet": a.get("wartet_auf"), "art": a.get("art"), "quelle": a.get("quelle", "dienst")})
    for a in liste:
        a["datum"] = datetime.date.fromisoformat(a["faellig"]) if a["faellig"] else None
    return sorted(liste, key=lambda a: (a["datum"] or datetime.date.max, a["titel"]))


def freie_bloecke(liste):
    """Luecken ab FREIER_BLOCK_MIN im Arbeitstag; Termine ausserhalb des Arbeitstags schneiden ihn nicht."""
    frei, zeiger = [], ARBEITSTAG[0]
    for t in liste + [{"von": ARBEITSTAG[1], "bis": ARBEITSTAG[1]}]:
        von = min(max(t["von"], ARBEITSTAG[0]), ARBEITSTAG[1])      # auf den Arbeitstag geschnitten
        if von - zeiger >= FREIER_BLOCK_MIN:
            frei.append((zeiger, von))
        zeiger = max(zeiger, min(t["bis"], ARBEITSTAG[1]))
    return frei


def uhr(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def dauer(m):
    return f"{m // 60} h {m % 60:02d}" if m >= 60 else f"{m} min"


def aufmerksamkeit(liste, term):
    """Reihum je Klasse, bis der Deckel voll ist: fuenfmal dasselbe Datum zeigt nichts."""
    hubs = {datenkopf(p).get("meeting_key"): p.stem for p in VAULT.rglob("*.md") if datenkopf(p).get("meeting_key")}
    klassen = {k: [] for k in KLASSEN}
    for a in liste:
        if a["datum"] and a["datum"] < HEUTE:
            klassen["ueberfaellig"].append(f"{a['titel']}, seit {(HEUTE - a['datum']).days} Tagen ueberfaellig")
        if a["wartet"]:
            klassen["wartet"].append(f"{a['titel']}: {a['wartet']}")
        if a["art"] == "entscheidung" and a["datum"] and (a["datum"] - HEUTE).days <= FENSTER_TAGE:
            klassen["entscheidung"].append(f"{a['titel']}, bis {a['datum']:%d.%m.}")
    for t in term:
        m = KUERZEL.match(t["betreff"])
        if m and m.group(1) in hubs:
            klassen["vorbereitung"].append(f"{uhr(t['von'])} {t['betreff']}: Hub «{hubs[m.group(1)]}» lesen")
    gewaehlt, runde = [], 0
    while len(gewaehlt) < DECKEL_AUFMERKSAMKEIT and any(klassen.values()):
        k = KLASSEN[runde % len(KLASSEN)]
        if klassen[k]:
            gewaehlt.append((k, klassen[k].pop(0)))
        runde += 1
    return gewaehlt


def einordnen(liste):
    gruppen = {"Erledigen": [], "Delegieren oder klaeren": [], "Einplanen": [], "Diese Woche sonst": []}
    for a in liste:
        if not a["datum"] or (a["datum"] - HEUTE).days > FENSTER_TAGE:
            continue
        dringend, wichtig = a["datum"] <= HEUTE, (a["prioritaet"] or "") in WICHTIG
        ziel = ("Erledigen" if dringend and wichtig else "Delegieren oder klaeren" if dringend
                else "Einplanen" if wichtig else "Diese Woche sonst")
        gruppen[ziel].append(f"{a['titel']} ({a['datum']:%d.%m.}, {a['quelle']})")
    return gruppen


def bauen():
    term, liste = termine(), aufgaben()
    frei = freie_bloecke(term)
    faellig = [a for a in liste if a["datum"] and a["datum"] <= HEUTE]
    ueber = [a for a in liste if a["datum"] and a["datum"] < HEUTE]
    groesster = max(frei, key=lambda f: f[1] - f[0], default=None)
    rubriken = []
    lage = (f"Der Tag gehoert {'vormittags' if groesster and groesster[0] < 12 * 60 else 'nachmittags'} dir: "
            f"{dauer(groesster[1] - groesster[0])} am Stueck ohne Termin." if groesster else "Kein freier Block ab 45 Minuten.")
    lage += f" {len(term)} Termine, {len(faellig)} Aufgaben bis heute faellig, davon {len(ueber)} ueberfaellig."
    rubriken.append(("Lage", [lage]))
    rubriken.append(("Kennzahlen", [f"Termine: {len(term)}", f"Faellig bis heute: {len(faellig)}",
                                    f"Ueberfaellig: {len(ueber)}",
                                    f"Fokus: {dauer(groesster[1] - groesster[0]) if groesster else 'keiner'}"]))
    rubriken.append(("Braucht deine Aufmerksamkeit", [f"[{k}] {s}" for k, s in aufmerksamkeit(liste, term)]))
    zeile = [f"{uhr(t['von'])}–{uhr(t['bis'])}  {t['betreff']}" for t in term]
    zeile += [f"{uhr(a)}–{uhr(b)}  frei, {dauer(b - a)}" for a, b in frei]
    rubriken.append(("Der Tag", sorted(zeile)))
    for name, eintraege in einordnen(liste).items():
        rubriken.append((name, eintraege))
    ohne_datum = sum(1 for a in liste if not a["datum"])
    spaeter = sum(1 for a in liste if a["datum"] and (a["datum"] - HEUTE).days > FENSTER_TAGE)
    ohne_prio = sum(1 for a in liste if a["datum"] and (a["datum"] - HEUTE).days <= FENSTER_TAGE and not a["prioritaet"])
    rubriken.append(("Fusszeile", [f"Nicht gezeigt: {ohne_datum} Aufgaben ohne Datum, {spaeter} mit Datum nach dem "
                                   f"{HEUTE + datetime.timedelta(days=FENSTER_TAGE):%d.%m.}.",
                                   f"Ohne Prioritaet und deshalb als nicht wichtig eingeordnet: {ohne_prio}."]))
    return [(n, e) for n, e in rubriken if e]                     # leere Rubriken entfallen


def als_text(rubriken):
    return "\n".join(f"## {n}\n" + "\n".join(f"- {z}" for z in e) + "\n" for n, e in rubriken)


def als_html(rubriken):
    teile = [f"<h2>{html.escape(n)}</h2><ul>" + "".join(f"<li>{html.escape(z)}</li>" for z in e) + "</ul>" for n, e in rubriken]
    return (f"<!doctype html><html lang=\"de\"><meta charset=\"utf-8\"><title>Briefing {HEUTE:%d.%m.%Y}</title>"
            "<style>body{font:15px/1.45 system-ui;max-width:42rem;margin:1.5rem auto;padding:0 1rem}h2{font-size:1rem;"
            "margin:1.2rem 0 .3rem;border-bottom:1px solid #ccc}ul{margin:0;padding-left:1.2rem}</style>"
            f"<h1>Briefing {WOCHENTAGE[HEUTE.weekday()]}, {HEUTE:%d.%m.%Y}</h1>" + "".join(teile) + "</html>")


def senden(seite, empfaenger):
    if empfaenger != EIGNER:
        sys.exit(f"ABBRUCH: Empfaenger {empfaenger} ist nicht der Eigner; dieses Programm sendet an niemanden sonst")
    name = f"briefing-{HEUTE.isoformat()}.html"
    if os.environ.get("BRIEFING_VERSAND_AUS") == "1":
        entwurf = pathlib.Path(os.environ.get("BRIEFING_ENTWUERFE", "/opt/vault/entwuerfe")) / name
        entwurf.parent.mkdir(parents=True, exist_ok=True); entwurf.write_text(seite, encoding="utf-8")
        print(f"BETRIEBSMELDUNG: Versand ausgefallen, Entwurf liegt unter {entwurf}", file=sys.stderr)
        return 69
    ausgang = pathlib.Path(os.environ.get("BRIEFING_AUSGANG", "/opt/vault/ausgang")) / name
    ausgang.parent.mkdir(parents=True, exist_ok=True)
    ausgang.write_text(f"An: {empfaenger}\nBetreff: Briefing {HEUTE:%d.%m.%Y}\n\n{seite}", encoding="utf-8")
    print(f"gesendet an {empfaenger}: {ausgang}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--html"); ap.add_argument("--senden", action="store_true")
    ap.add_argument("--an", default=EIGNER, help="nur fuer die Probe des Riegels; erlaubt ist allein die Konstante")
    a = ap.parse_args()
    rubriken = bauen()
    print(als_text(rubriken))
    if a.html:
        pathlib.Path(a.html).write_text(als_html(rubriken), encoding="utf-8")
    if a.senden:
        sys.exit(senden(als_html(rubriken), a.an))
