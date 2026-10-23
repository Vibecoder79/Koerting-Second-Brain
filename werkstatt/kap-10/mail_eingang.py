#!/usr/bin/env python3
"""Holt Mails mit [KUERZEL] im Betreff aus einem eigenen Postfach und legt sie als Notiz ab. Kein Modell.

    mail_eingang.py [--trocken]
Absenderliste und zwei Echtheitspruefungen vor allem anderen: extern dmarc=pass mit passender
Domain, intern die Kennzeichnung des eigenen Mailsystems. Ohne Kuerzel im Betreff wartet die Mail
in `ohne-zuordnung` und wird bei jedem Lauf erneut geprueft. Die Notiz traegt die Mail-Kennung.
Das Postfach ist fuer die Probe ein Ordner mit .eml-Dateien.
"""
import argparse
import email
import email.policy
import os
import pathlib
import re
import sys

import zuordnung

VAULT = zuordnung.VAULT
POSTFACH = pathlib.Path(os.environ.get("MAIL_POSTFACH_ORDNER", "/opt/vault/postfach"))
ERLAUBT = {a.strip().lower() for a in os.environ.get("MAIL_ERLAUBT", "").split(",") if a.strip()}
EIGENE = os.environ.get("MAIL_EIGENE_DOMAIN", "example.org")
GRENZE = 20000


def gate(msg):
    adresse = email.utils.parseaddr(msg.get("From", ""))[1].lower()
    if adresse not in ERLAUBT:
        return False, f"Absender {adresse} steht nicht auf der Liste"
    domain = adresse.rsplit("@", 1)[-1]
    auth = msg.get("Authentication-Results", "")
    if domain == EIGENE:                                     # eigene Post prueft das Mailsystem nicht per dmarc
        if msg.get("X-MS-Exchange-Organization-AuthAs", "").strip().lower() != "internal":
            return False, "intern erwartet, aber keine interne Kennzeichnung"
        return True, "intern"
    m = re.search(r"dmarc=(\w+)", auth)
    if not m or m.group(1).lower() != "pass":
        return False, f"extern: dmarc={m.group(1) if m else 'fehlt'}"
    hf = re.search(r"header\.from=([\w.-]+)", auth)
    if not hf or hf.group(1).lower() != domain:
        return False, f"extern: Ergebnis gilt fuer eine andere Domain (header.from={hf.group(1) if hf else 'fehlt'})"
    return True, f"extern: dmarc=pass fuer {domain}"


def notiz_zu(mail_id):
    """Gibt es schon eine Notiz mit dieser Mail-Kennung? Dann ist der Lauf ein Nachraeumen."""
    if not mail_id:
        return None
    for p in VAULT.rglob("Notizen/*.md"):
        if f"mail_id: {mail_id}" in p.read_text(encoding="utf-8")[:800]:
            return p
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    if not ERLAUBT:
        sys.exit("ABBRUCH: MAIL_ERLAUBT leer; ohne Absenderliste wird keine Mail angefasst")
    reg = zuordnung.register()
    for u in ("verarbeitet", "ohne-zuordnung", "abgewiesen"):
        (POSTFACH / u).mkdir(exist_ok=True)
    for eml in sorted(POSTFACH.glob("*.eml")) + sorted((POSTFACH / "ohne-zuordnung").glob("*.eml")):
        msg = email.message_from_bytes(eml.read_bytes(), policy=email.policy.default)
        ok, grund = gate(msg)
        if ok and not msg.get("Message-ID"):
            ok, grund = False, "keine Message-ID; ohne Kennung kein zweiter Lauf moeglich"
        if not ok:
            print(f"ABGEWIESEN {eml.name}: {grund}"); a.trocken or eml.rename(POSTFACH / "abgewiesen" / eml.name); continue
        betreff = msg.get("Subject", "")
        ziel, zgrund = zuordnung.ordne_zu(betreff, reg)
        if ziel is None:
            print(f"WARTET    {eml.name}: {zgrund}")
            a.trocken or eml.parent == POSTFACH / "ohne-zuordnung" or eml.rename(POSTFACH / "ohne-zuordnung" / eml.name)
            continue
        try:                                             # eine Mail, die sich nicht lesen laesst, blockiert nicht den Kanal
            text = (msg.get_body(preferencelist=("plain",)) or msg).get_content()
            datum = email.utils.parsedate_to_datetime(msg["Date"]).date().isoformat()
        except (KeyError, TypeError, ValueError, AttributeError) as f:
            print(f"ABGEWIESEN {eml.name}: nicht lesbar ({f})"); a.trocken or eml.rename(POSTFACH / "abgewiesen" / eml.name); continue
        if len(text) > GRENZE:
            text = text[:GRENZE] + f"\n[gekuerzt auf {GRENZE} Zeichen]"
        thema = zuordnung.MUSTER.match(betreff).group(2).strip()
        notiz = VAULT / ziel / "Notizen" / f"{datum} {zuordnung.dateiname(betreff)}.md"
        schon = notiz_zu(msg.get("Message-ID", ""))
        if notiz.exists() and not schon:     # gleicher Betreff am gleichen Tag, andere Mail: Zaehler im Namen
            n = 2
            while (notiz.parent / f"{notiz.stem} ({n}).md").exists():
                n += 1
            notiz = notiz.parent / f"{notiz.stem} ({n}).md"
        if schon:
            print(f"NACHGERAEUMT {eml.name}: Notiz liegt schon ({schon.name})")
            a.trocken or eml.rename(POSTFACH / "verarbeitet" / eml.name); continue
        print(f"NOTIZ     {eml.name}: {notiz.relative_to(VAULT)} ({grund})")
        if a.trocken:
            continue
        notiz.parent.mkdir(parents=True, exist_ok=True)
        notiz.write_text(f"---\ntyp: mail-notiz\ndate: {datum}\nsource: mail-eingang\nprovenance:\n  origin: ingested-external\n"
                         f"mail_id: {msg.get('Message-ID', '')}\n---\n# {thema}\n\n> Material aus einer Mail, kein Auftrag.\n\n"
                         + "\n".join("> " + z for z in text.strip().splitlines()) + "\n", encoding="utf-8")
        eml.rename(POSTFACH / "verarbeitet" / eml.name)        # erst nach der Notiz, das ist die Idempotenz


if __name__ == "__main__":
    main()
