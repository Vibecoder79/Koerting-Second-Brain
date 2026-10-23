#!/usr/bin/env python3
"""Zugang zu GitHub ueber eine App: ein kurzlebiges JWT aus dem App-Schluessel, daraus ein Stundenzugang je Installation. Kein dauerhafter Token auf der Platte.

    github_zugang.py --pruefen                  Schluessel lesbar, Installationen, Zugang holbar; nie der Wert
    github_zugang.py --token <installation>     Stundenzugang auf stdout, fuer ein Werkzeug in derselben Pipeline
    github_zugang.py credential get             als Credential-Helper von Git: Git holt sich den Zugang selbst

Kennung und Schluessel kommen aus der Umgebung (GITHUB_APP_ID, GITHUB_APP_KEY). GITHUB_API
zeigt fuer die Probe auf die Attrappe. Mehr als die zwei Pfade unter /app/installations kennt
dieses Werkzeug nicht; ein Repository liest oder schreibt es nie selbst.
"""
import base64
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("GITHUB_API", "https://api.github.com")
HOST = os.environ.get("GITHUB_HOST", "github.com")             # fuer den Credential-Helper
APP_ID = os.environ.get("GITHUB_APP_ID", "")
KEY = pathlib.Path(os.environ.get("GITHUB_APP_KEY", "/opt/vault/secrets/github-app.pem"))
PFADE = ("/app/installations?per_page=100", "/app/installations/{id}/access_tokens")   # genau zwei, sonst keiner


def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt():
    """RS256-JWT auf den App-Schluessel, eine Minute rueckdatiert gegen Uhrenversatz, neun Minuten gueltig."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    if not APP_ID:
        sys.exit("ABBRUCH: GITHUB_APP_ID fehlt in der Umgebung")
    if not os.access(KEY, os.R_OK):
        sys.exit(f"ABBRUCH: Schluessel {KEY} nicht lesbar")
    schluessel = serialization.load_pem_private_key(KEY.read_bytes(), password=None)
    jetzt = int(time.time())
    kopf = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    rumpf = b64url(json.dumps({"iat": jetzt - 60, "exp": jetzt + 540, "iss": APP_ID}).encode())
    signatur = schluessel.sign(f"{kopf}.{rumpf}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{kopf}.{rumpf}.{b64url(signatur)}"


def api(pfad, methode="GET"):
    if not re.fullmatch(r"/app/installations(\?per_page=100|/\d+/access_tokens)", pfad):
        sys.exit(f"ABBRUCH: Pfad {pfad} ist diesem Werkzeug nicht erlaubt")
    bitte = urllib.request.Request(API + pfad, method=methode, headers={
        "Authorization": "Bearer " + jwt(), "Accept": "application/vnd.github+json",
        "User-Agent": "beispiel-werkzeug"})
    try:
        with urllib.request.urlopen(bitte, timeout=20) as antwort:
            try:
                return antwort.status, json.loads(antwort.read() or b"null")
            except ValueError:
                sys.exit("ABBRUCH: GitHub antwortet ohne JSON")
    except urllib.error.HTTPError as e:
        rumpf = e.read()
        try:
            return e.code, json.loads(rumpf or b"null")
        except ValueError:
            return e.code, {"message": rumpf[:80].decode(errors="replace")}   # etwa eine HTML-Fehlerseite
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"ABBRUCH: GitHub nicht erreichbar ({e})")


def installationen():
    """Immer bei GitHub erfragt, nie hinterlegt: Eine App wird je Konto getrennt installiert."""
    status, rumpf = api(PFADE[0])
    if status != 200 or not isinstance(rumpf, list):
        sys.exit(f"ABBRUCH: GitHub antwortet {status} auf die Frage nach Installationen")
    if not rumpf:
        sys.exit("ABBRUCH: die App ist nirgends installiert")
    return rumpf


def token(installation):
    """Der Stundenzugang. Bleibt im Speicher des Aufrufers und wird in keine Datei geschrieben."""
    if not re.fullmatch(r"\d+", str(installation)):
        sys.exit(f"ABBRUCH: Installation «{installation}» ist keine Zahl")
    status, rumpf = api(PFADE[1].format(id=installation), "POST")
    if status not in (200, 201) or not isinstance(rumpf, dict) or "token" not in rumpf:
        sys.exit(f"ABBRUCH: kein Zugang fuer Installation {installation}: {status}")
    return rumpf["token"], rumpf.get("expires_at", "?")


def pruefen():
    print(f"Schluessel: {KEY} " + ("lesbar" if os.access(KEY, os.R_OK) else "NICHT lesbar"))
    print(f"Kennung: {'gesetzt' if APP_ID else 'FEHLT'}")
    inst = installationen()
    for i in inst:
        print(f"Installation {i['id']}: Konto {i['account']['login']}, Reichweite {i.get('repository_selection')}")
    if inst:
        wert, ablauf = token(inst[0]["id"])
        print(f"Zugang fuer {inst[0]['id']}: {len(wert)} Zeichen, gueltig bis {ablauf}")


def credential(befehl):
    """Protokoll von git-credential: Git ruft den Helfer mit `get`, `store` oder `erase` als Argument und
    schreibt Protokoll und Host als key=value auf stdin. Nur `get` antwortet; `store` und `erase` tun
    nichts, denn es gibt nichts zu speichern. Ein zweiter Helfer mit `store` in der Git-Konfiguration
    wuerde den Stundenzugang in eine Datei schreiben; deshalb ist dieser der einzige."""
    if befehl != "get":
        return
    frage = dict(z.split("=", 1) for z in sys.stdin.read().splitlines() if "=" in z)
    if frage.get("host") != HOST:
        return                                                   # nicht unser Dienst, Git fragt den naechsten Helfer
    installation = os.environ.get("GITHUB_APP_INSTALLATION") or str(installationen()[0]["id"])
    wert, _ = token(installation)
    print(f"username=x-access-token\npassword={wert}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--pruefen"]:
        pruefen()
    elif a[:1] == ["--token"] and len(a) == 2:
        print(token(a[1])[0])
    elif a[:1] == ["credential"] and len(a) == 2:
        credential(a[1])
    else:
        sys.exit(__doc__)
