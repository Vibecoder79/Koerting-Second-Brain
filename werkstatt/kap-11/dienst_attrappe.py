#!/usr/bin/env python3
"""Attrappe eines bezahlten Dienstes mit Idempotenz-Schluessel: gleicher Schluessel, gleicher Job. Zaehlt jede Bestellung.

    dienst_attrappe.py <port>
Liegt die Datei aus ATTRAPPE_HAENGT vor, nimmt die Attrappe die Bestellung an und antwortet
erst nach sechs Sekunden: der Fall «angekommen, aber keine Quittung». Mit ATTRAPPE_STATUS=503
antwortet sie wie ein Proxy, der den Dienst nicht erreicht, ohne die Bestellung anzunehmen.
"""
import http.server
import json
import os
import secrets
import sys
import time

HAENGT = os.environ.get("ATTRAPPE_HAENGT", "/nicht/vorhanden")
LOG = os.environ.get("ATTRAPPE_LOG", "dienst.log")
JOBS = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def antwort(self, status, daten):
        with open(LOG, "a") as f:                                # protokolliert, bevor die Quittung rausgeht
            f.write(f"{self.command} {self.path} {status}\n")
        rumpf = json.dumps(daten).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(rumpf))); self.end_headers(); self.wfile.write(rumpf)

    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path != "/bestellungen" or not self.headers.get("Authorization", "").startswith("Bearer "):
            return self.antwort(401, {"error": "kein Zugang"})
        if os.environ.get("ATTRAPPE_STATUS"):
            return self.antwort(int(os.environ["ATTRAPPE_STATUS"]), {"error": "Attrappe"})
        schluessel = self.headers.get("Idempotency-Key")
        if not schluessel:
            return self.antwort(400, {"error": "Idempotency-Key fehlt"})
        if schluessel in JOBS:
            return self.antwort(200, JOBS[schluessel])
        JOBS[schluessel] = {"job": "job-" + secrets.token_hex(4), "schluessel": schluessel}
        if os.path.exists(HAENGT):
            time.sleep(6)                                        # bestellt ist es trotzdem
        try:
            self.antwort(201, JOBS[schluessel])
        except BrokenPipeError:
            pass                                                 # der Besteller hat nicht gewartet

    def do_GET(self):
        schluessel = self.path.rsplit("/", 1)[-1]
        if self.path.startswith("/bestellungen/") and schluessel in JOBS:
            return self.antwort(200, JOBS[schluessel])
        self.antwort(404, {"error": "unbekannt"})


http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
