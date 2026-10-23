#!/usr/bin/env python3
"""Prueft den Kopf einer Helfer-Datei: die fuenf Pflichtfelder muessen da sein, model eine bekannte Stufe."""
import pathlib
import re
import sys

PFLICHT = ("name", "description", "tools", "model", "effort")
t = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
kopf = t.split("---")[1] if t.startswith("---") else ""
felder = dict(re.findall(r"^(\w+):\s*(.*)$", kopf, re.M))
fehlt = [f for f in PFLICHT if not felder.get(f)]
if fehlt or felder.get("model") not in ("haiku", "sonnet", "opus"):
    print(f"BEFUND {sys.argv[1]}: fehlt {fehlt}, model={felder.get('model')}"); sys.exit(1)
print(f"OK {sys.argv[1]}: model={felder['model']}, effort={felder['effort']}, tools={felder['tools']}")
