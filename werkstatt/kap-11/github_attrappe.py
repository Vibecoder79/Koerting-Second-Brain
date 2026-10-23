#!/usr/bin/env python3
"""Attrappe fuer die App-Schnittstelle von GitHub: prueft das JWT gegen den oeffentlichen Schluessel, kennt eine Installation, gibt Stundenzugaenge aus und zaehlt jeden Aufruf.

    github_attrappe.py <port>
Umgebung: ATTRAPPE_PUB (oeffentlicher Schluessel), ATTRAPPE_APP_ID (erwartete Kennung),
ATTRAPPE_LOG (eine Zeile je Aufruf: Methode, Pfad, Status). Der Zugang steht nie im Protokoll.
"""
import base64
import http.server
import json
import os
import secrets
import sys
import time

PUB = os.environ["ATTRAPPE_PUB"]
APP_ID = os.environ.get("ATTRAPPE_APP_ID", "")
LOG = os.environ.get("ATTRAPPE_LOG", "attrappe.log")
INSTALLATIONEN = [{"id": 101, "account": {"login": "beispiel-org"}, "repository_selection": "selected"}]


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def jwt_gueltig(kopfzeile):
    """Signatur, Aussteller und Zeitfenster. Ein JWT ueber zehn Minuten lehnt GitHub ab."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    try:
        kopf, rumpf, sig = kopfzeile.removeprefix("Bearer ").split(".")
        pub = serialization.load_pem_public_key(open(PUB, "rb").read())
        pub.verify(b64d(sig), f"{kopf}.{rumpf}".encode(), padding.PKCS1v15(), hashes.SHA256())
        daten = json.loads(b64d(rumpf))
        jetzt = time.time()
        return daten.get("iss") == APP_ID and daten["iat"] <= jetzt < daten["exp"] and daten["exp"] - daten["iat"] <= 600
    except Exception:
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    def antwort(self, status, daten):
        rumpf = json.dumps(daten).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(rumpf))); self.end_headers(); self.wfile.write(rumpf)
        with open(LOG, "a") as f:
            f.write(f"{self.command} {self.path} {status}\n")

    def log_message(self, *a):
        pass

    def do_GET(self):
        if not jwt_gueltig(self.headers.get("Authorization", "")):
            return self.antwort(401, {"message": "Bad credentials"})
        if self.path.startswith("/app/installations"):
            return self.antwort(200, INSTALLATIONEN)
        self.antwort(404, {"message": "Not Found"})

    def do_POST(self):
        if not jwt_gueltig(self.headers.get("Authorization", "")):
            return self.antwort(401, {"message": "Bad credentials"})
        if self.path == "/app/installations/101/access_tokens":
            ablauf = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))
            return self.antwort(201, {"token": "ghs_" + secrets.token_hex(18), "expires_at": ablauf})
        self.antwort(404, {"message": "Not Found"})


http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
