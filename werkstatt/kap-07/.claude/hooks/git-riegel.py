#!/usr/bin/env python3
"""Git-Riegel, Kern: Befehl aus dem JSON-Eingang gegen die Musterdatei halten, bei Treffer verweigern."""
import json
import os
import re
import sys


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"systemMessage": "GIT-RIEGEL: Eingang nicht lesbar, Riegel fuer diesen Aufruf INAKTIV."}))
        return 0
    cmd = (d.get("tool_input") or {}).get("command")
    if not isinstance(cmd, str):          # kein Shell-Befehl: nichts zu pruefen
        return 0
    meldungen = []                        # genau ein JSON-Objekt am Ende
    for zeile in open(os.environ["GIT_RIEGEL_MUSTER"], encoding="utf-8"):
        if not zeile.strip() or zeile.startswith("#") or "\t" not in zeile:
            continue
        muster, grund = zeile.rstrip("\n").split("\t", 1)
        try:
            # Die Muster begrenzen sich mit [^;&|]* auf den einzelnen Befehl. Zwei Grenzen: Ein
            # Zeilenumbruch gilt dem Muster als Teil desselben Befehls (noetig fuer eine mehrzeilige
            # Commit-Nachricht), und ein ; & | in der Nachricht sperrt einen gueltigen Commit.
            if re.search(muster, cmd, re.M):
                antwort = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                           "permissionDecision": "deny",
                           "permissionDecisionReason": "GIT-RIEGEL: " + grund.strip()}}
                if meldungen:
                    antwort["systemMessage"] = " ".join(meldungen)
                print(json.dumps(antwort, ensure_ascii=False))
                return 0
        except re.error as f:
            meldungen.append(f"GIT-RIEGEL: kaputtes Muster ({f}), Zeile uebersprungen.")
    if meldungen:
        print(json.dumps({"systemMessage": " ".join(meldungen)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
