#!/usr/bin/env python3
"""Zugang zu Microsoft Graph ohne Benutzer, mit einem Riegel vor allem Unumkehrbaren.

token() holt das Zugangstoken, aufruf() fuehrt einen Aufruf aus, eingriff_geschuetzt() ist der
Riegel davor. Basisadressen sind fuer die Probe ueberschreibbar; der Schluessel wird nie ausgegeben.
"""
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ZUGANG = pathlib.Path(os.environ.get("GRAPH_ZUGANG", "/opt/vault/secrets/mail.env"))
LOGIN = os.environ.get("GRAPH_LOGIN", "https://login.microsoftonline.com")
BASIS = os.environ.get("GRAPH_BASIS", "https://graph.microsoft.com/v1.0")
GESCHUETZT = ("DELETE", "PATCH", "PUT")
UMKEHRBAR = frozenset({"description", "displayName", "theme"})   # abschliessend; visibility fehlt bewusst:
                                                                 # privat auf oeffentlich legt Inhalt offen, das nimmt kein zweiter Aufruf zurueck
# POST-Pfade, deren Folge nicht zurueckzunehmen ist: absagen, endgueltig loeschen, verschieben, senden
POST_UNUMKEHRBAR = ("/cancel", "/permanentDelete", "/move", "/decline", "/accept", "/tentativelyAccept",
                    "/send", "/sendMail", "/reply", "/replyAll", "/forward")
DAUERHAFT, VORUEBERGEHEND = 77, 69


class Gebremst(Exception):
    """Der Aufruf braucht eine Freigabe und ist NICHT hinausgegangen."""


def zugang():
    werte = {}
    try:
        text = ZUGANG.read_text(encoding="utf-8")
    except OSError as f:
        print(f"Zugangsdatei nicht lesbar ({f.strerror}): dauerhaft"); raise SystemExit(DAUERHAFT)
    for zeile in text.splitlines():
        if "=" in zeile and not zeile.startswith("#"):
            k, v = zeile.split("=", 1); werte[k.strip()] = v.strip()
    fehlend = [k for k in ("TENANT_ID", "CLIENT_ID", "CLIENT_SECRET") if not werte.get(k)]
    if fehlend:
        raise SystemExit(f"Zugang unvollstaendig, es fehlt {fehlend}; nichts wird ersatzweise geholt")
    return werte


def token():
    """Client-Credentials-Fluss: die App handelt als eigene Identitaet mit genau ihren Rollen."""
    z = zugang()
    daten = urllib.parse.urlencode({"client_id": z["CLIENT_ID"], "client_secret": z["CLIENT_SECRET"],
                                    "scope": "https://graph.microsoft.com/.default",
                                    "grant_type": "client_credentials"}).encode()
    try:
        with urllib.request.urlopen(f"{LOGIN}/{z['TENANT_ID']}/oauth2/v2.0/token", data=daten, timeout=30) as a:
            return json.loads(a.read())["access_token"]
    except urllib.error.HTTPError as f:                       # 400/401/403: falsche Zugangsdaten, wiederholen hilft nie; 429/5xx: spaeter
        dauerhaft = f.code in (400, 401, 403)
        print(f"Anmeldung abgelehnt ({f.code}): {'dauerhaft' if dauerhaft else 'voruebergehend'}")
        raise SystemExit(DAUERHAFT if dauerhaft else VORUEBERGEHEND)
    except urllib.error.URLError:
        print("Anmeldedienst nicht erreichbar: voruebergehend"); raise SystemExit(VORUEBERGEHEND)


def eingriff_geschuetzt(methode, pfad, rumpf=None):
    if methode == "POST" and pfad.split("?", 1)[0].rstrip("/").endswith(POST_UNUMKEHRBAR):   # auch mit Query oder Schraegstrich
        return True
    if methode not in GESCHUETZT:
        return False
    if methode == "DELETE":
        return True
    if not rumpf:                                           # ohne Rumpf ist die Folge nicht beurteilbar
        return True
    return not set(rumpf).issubset(UMKEHRBAR)


def aufruf(tok, methode, pfad, rumpf=None, freigabe=""):
    if eingriff_geschuetzt(methode, pfad, rumpf) and not freigabe:
        raise Gebremst(f"{methode} {pfad} braucht eine erteilte Freigabe; der Aufruf ist nicht hinausgegangen")
    req = urllib.request.Request(BASIS + pfad, method=methode,
                                 data=json.dumps(rumpf).encode() if rumpf is not None else None,
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as a:
            text = a.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as f:
        dauerhaft = f.code in (400, 401, 403, 404)                # falsche Zugangsdaten oder Rechte: wiederholen hilft nie
        print(f"Graph {f.code} bei {methode} {pfad}: {'dauerhaft' if dauerhaft else 'voruebergehend'}")
        raise SystemExit(DAUERHAFT if dauerhaft else VORUEBERGEHEND)
    except urllib.error.URLError as f:
        print(f"Graph nicht erreichbar bei {methode} {pfad}: voruebergehend")
        raise SystemExit(VORUEBERGEHEND)
