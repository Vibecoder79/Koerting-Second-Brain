#!/usr/bin/env python3
"""Attrappe fuer Anmeldedienst und Graph: antwortet wie der Dienst, merkt sich Entwuerfe, zaehlt jeden Aufruf.
Rollen im Token kommen aus ATTRAPPE_ROLLEN (kommagetrennt); ATTRAPPE_STATUS laesst jeden schreibenden Graph-Aufruf
mit diesem Statuscode scheitern (Probe fuer 403), ATTRAPPE_GET_STATUS jeden lesenden, ATTRAPPE_TOKEN_STATUS die Anmeldung. Nur fuer die Probe, kein Netz nach aussen."""
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ENTWUERFE, PROTOKOLL = {}, open(os.environ.get("ATTRAPPE_LOG", "attrappe.log"), "a")


def token_mit(rollen):
    kopf = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    nutz = base64.urlsafe_b64encode(json.dumps({"roles": rollen}).encode()).rstrip(b"=").decode()
    return f"{kopf}.{nutz}.attrappe"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def antwort(self, code, obj):
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def rumpf(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n).decode() if n else ""

    def do_POST(self):
        r = self.rumpf(); PROTOKOLL.write(f"POST {self.path}\n"); PROTOKOLL.flush()
        if self.path.endswith("/oauth2/v2.0/token"):
            if os.environ.get("ATTRAPPE_TOKEN_STATUS"):
                return self.antwort(int(os.environ["ATTRAPPE_TOKEN_STATUS"]), {"error": "Attrappe"})
            return self.antwort(200, {"access_token": token_mit(os.environ.get("ATTRAPPE_ROLLEN", "").split(","))})
        if os.environ.get("ATTRAPPE_STATUS"):
            return self.antwort(int(os.environ["ATTRAPPE_STATUS"]), {"error": "Attrappe"})
        if "/messages" in self.path:
            d = json.loads(r); kennung = f"AAMk{len(ENTWUERFE) + 1}"
            ENTWUERFE[kennung] = {**d, "id": kennung, "isDraft": True}
            return self.antwort(201, ENTWUERFE[kennung])
        self.antwort(200, {})

    def do_GET(self):
        PROTOKOLL.write(f"GET {self.path}\n"); PROTOKOLL.flush()
        if os.environ.get("ATTRAPPE_GET_STATUS"):
            return self.antwort(int(os.environ["ATTRAPPE_GET_STATUS"]), {"error": "Attrappe"})
        kennung = self.path.rsplit("/", 1)[-1]
        self.antwort(200, ENTWUERFE.get(kennung, {}))

    def do_PATCH(self):
        self.rumpf(); PROTOKOLL.write(f"PATCH {self.path}\n"); PROTOKOLL.flush(); self.antwort(204, {})

    def do_DELETE(self):
        PROTOKOLL.write(f"DELETE {self.path}\n"); PROTOKOLL.flush(); self.antwort(204, {})


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
