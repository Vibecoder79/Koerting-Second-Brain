#!/usr/bin/env python3
"""Ein Projekt anlegen: Ordner, Hub, Governance, sieben Unterordner. Trockenlauf ist die Vorgabe.

Aufruf:  python3 werkzeuge/anlegen.py --name "Beispielprojekt" --kuerzel BSP [--ausfuehren]
Prueft das Kuerzel gegen die Regel und gegen alle Koepfe im Vault, bevor etwas entsteht.
"""
import argparse
import datetime
import pathlib
import re
import sys

VAULT = pathlib.Path(__file__).resolve().parents[1]
VORLAGEN = VAULT / "00 Kontext" / "Vorlagen"
UNTERORDNER = ["Meetings", "Decisions", "Research", "Journal", "Kommunikation", "assets", "Notizen"]
KUERZEL = re.compile(r"^[A-Z0-9]{2,6}(-[A-Z0-9]{2,8})?$")
SCHLUESSEL = re.compile(r"^meeting_key:\s*(\S+)", re.M)


def register():
    """Alle vergebenen Kuerzel, aus den Koepfen gelesen. Es gibt keine zweite Liste."""
    gefunden = {}
    for p in VAULT.rglob("*.md"):
        if "Vorlagen" in p.parts:
            continue
        kopf = p.read_text(encoding="utf-8", errors="replace")[:2000]
        m = SCHLUESSEL.search(kopf)
        if m:
            gefunden[m.group(1)] = p.relative_to(VAULT).as_posix()
    return gefunden


def kuerzel_pruefen(k, vergeben):
    fehler = []
    if not KUERZEL.match(k) or not re.search(r"[A-Z]", k):
        fehler.append("Form: 2 bis 6 Grossbuchstaben oder Ziffern, mindestens ein Buchstabe, optional -TEIL; kein Datum")
    if k in vergeben:
        fehler.append(f"vergeben an {vergeben[k]}")
    for v in vergeben:
        if v.startswith(k + "-") or k.startswith(v + "-"):
            fehler.append(f"mehrdeutig zu {v} ({vergeben[v]}): ein Stamm darf nicht Praefix eines anderen sein")
    return fehler


def fuellen(vorlage, werte):
    text = (VORLAGEN / vorlage).read_text(encoding="utf-8")
    for k, v in werte.items():
        text = text.replace("{{" + k + "}}", v)
    rest = re.findall(r"{{\w+}}", text)
    if rest:
        sys.exit(f"ABBRUCH: Platzhalter ohne Wert in {vorlage}: {rest}")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baum", default="02 Projekte")
    ap.add_argument("--name", required=True)
    ap.add_argument("--kuerzel", required=True)
    ap.add_argument("--source", default="mensch")
    ap.add_argument("--ausfuehren", action="store_true")
    a = ap.parse_args()

    if re.search(r"\d{4}-\d{2}", a.name):
        sys.exit("ABBRUCH: kein Datum im Projektnamen; Start und Ende stehen im Kopf")
    fehler = kuerzel_pruefen(a.kuerzel, register())
    if fehler:
        sys.exit("ABBRUCH, Kuerzel " + a.kuerzel + ":\n  - " + "\n  - ".join(fehler))
    ziel = VAULT / a.baum / a.name
    if ziel.exists():
        sys.exit(f"ABBRUCH: {ziel.relative_to(VAULT)} gibt es schon")

    heute = datetime.date.today().isoformat()
    werte = {"NAME": a.name, "KUERZEL": a.kuerzel, "DATUM": heute, "SOURCE": a.source,
             "PFAD": f"{a.baum}/{a.name}"}
    hub = fuellen("Projekt-Hub.md", werte)
    gov = fuellen("Projekt-Governance.md", werte)

    print(("ANLEGEN" if a.ausfuehren else "TROCKENLAUF") + f": {a.baum}/{a.name}/")
    print(f"  {a.name} - Hub.md   (meeting_key {a.kuerzel})")
    print("  Projekt-Governance.md   (projekt_art und backlog_tool bleiben leer: Eigner-Felder)")
    for u in UNTERORDNER:
        print(f"  {u}/.gitkeep")
    if not a.ausfuehren:
        print("Nichts geschrieben. Mit --ausfuehren anlegen.")
        return
    ziel.mkdir(parents=True)
    (ziel / f"{a.name} - Hub.md").write_text(hub, encoding="utf-8")
    (ziel / "Projekt-Governance.md").write_text(gov, encoding="utf-8")
    for u in UNTERORDNER:
        (ziel / u).mkdir()
        (ziel / u / ".gitkeep").write_text("", encoding="utf-8")
    print("Angelegt. Jetzt gezielt committen: git add -- \"" + f"{a.baum}/{a.name}" + "\"")


if __name__ == "__main__":
    main()
