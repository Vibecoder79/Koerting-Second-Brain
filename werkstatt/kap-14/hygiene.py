#!/usr/bin/env python3
"""Hygiene-Messung des Vaults ohne Modell: tote und mehrdeutige Verweise, fehlendes Pflichtfeld, verwaiste Notizen. Misst immer, repariert nur nach Positivliste und nur auf Befehl.

    hygiene.py                 messen, Zeitreihe anhaengen
    hygiene.py --reparieren    dazu: tote Verweise mit genau einem Ziel umschreiben, ein eigener Commit;
                               von Hand nur in der Huelle: mit-sperre.sh -- hygiene.py --reparieren
    hygiene.py --selbsttest    Parser gegen die bekannten Messfehler

Die Zeitreihe liegt im Vault (Vault-Gesundheit/kennzahlen.tsv) und wird von der Nachernte der
Sperre aus Kapitel 5 committet, der Bericht geht auf stdout. Warteraum und Archiv repariert es nie. Aendert
sich die Messung, zaehlt MESSUNG hoch und die Zeitreihe bekommt eine Bruchzeile, damit niemand
eine neue Zaehlweise als Verfall liest.
"""
import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys
import tempfile

VAULT = pathlib.Path(os.environ.get("VAULT_DIR", "/opt/vault/work/vault"))
MESSUNG = 1                                                  # Fassung der Messlogik
AUSGENOMMEN = ("Vault-Gesundheit", "05 Daily Notes")         # kein Kandidat fuer «verwaist»
NIE_SCHREIBEN = ("08 Meeting Inbox", "06 Archiv")             # Warteraum und Archiv repariert niemand
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
LINK = re.compile(r"\[\[([^\]|#\\]+)(?:#[^\]|\\]*)?(?:\\?\|[^\]]*)?\]\]")


def datenkopf_und_rumpf(text):
    if text.startswith("---\n") and "\n---\n" in text:
        kopf, rumpf = text[4:].split("\n---\n", 1)
        return kopf, rumpf
    return "", text


def links(text):
    """Nur aus dem Rumpf, nie aus Code: `[[x]]` in Code ist ein Beispiel, kein Verweis."""
    return [m.group(1).strip() for m in LINK.finditer(CODE.sub("", datenkopf_und_rumpf(text)[1]))]


def messen():
    alle = [p for p in VAULT.rglob("*") if p.is_file() and not p.parts[len(VAULT.parts)].startswith(".")]
    dateien = [p for p in alle if p.suffix == ".md"]
    namen = {}
    for p in dateien:
        namen.setdefault(p.stem, []).append(p)
    for p in alle:                                           # Anhang oder .base: der Verweis traegt die Endung
        if p.suffix != ".md":
            namen.setdefault(p.name, []).append(p)
    klein = {}
    for stem in namen:
        klein.setdefault(stem.lower(), []).append(stem)
    tote, mehrdeutig, ohne_source, eingehend, reparabel = [], [], [], set(), []
    for p in dateien:
        text = p.read_text(encoding="utf-8", errors="replace")
        kopf, _ = datenkopf_und_rumpf(text)
        if not re.search(r"^source:\s*\S", kopf, re.M):
            ohne_source.append(p)
        for ziel in links(text):
            ziel = ziel.rsplit("/", 1)[-1]                   # [[Ordner/Notiz]]: Obsidian loest ueber den Namen auf
            if ziel in namen:
                eingehend.add(ziel)
                if len(namen[ziel]) > 1:
                    mehrdeutig.append((p, ziel))
            else:
                tote.append((p, ziel))
                kandidaten = klein.get(ziel.lower(), [])
                if len(kandidaten) == 1 and len(namen[kandidaten[0]]) == 1:
                    reparabel.append((p, ziel, kandidaten[0]))     # genau ein Ziel: Positivliste
    verwaist = [p for p in dateien if p.stem not in eingehend and not any(a in p.parts for a in AUSGENOMMEN)]
    return {"notizen": len(dateien), "tote": tote, "mehrdeutig": mehrdeutig, "ohne_source": ohne_source,
            "verwaist": verwaist, "reparabel": reparabel}


def zeitreihe(m):
    datei = VAULT / "Vault-Gesundheit" / "kennzahlen.tsv"
    datei.parent.mkdir(exist_ok=True)
    zeilen = datei.read_text(encoding="utf-8").splitlines() if datei.exists() else ["datum\tmessung\tnotizen\ttote\tmehrdeutige\tohne_source\tverwaist"]
    letzte = [z for z in zeilen[1:] if not z.startswith("#")]
    if letzte and letzte[-1].split("\t")[1] != str(MESSUNG):
        zeilen.append(f"# Bruch: Messung v{letzte[-1].split(chr(9))[1]} -> v{MESSUNG}, Werte davor nicht vergleichbar")
    zeilen.append(f"{datetime.date.today()}\t{MESSUNG}\t{m['notizen']}\t{len(m['tote'])}\t{len(m['mehrdeutig'])}\t{len(m['ohne_source'])}\t{len(m['verwaist'])}")
    datei.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return datei


def reparieren(m):
    """Positivliste: ein toter Verweis, fuer den es genau eine Datei gibt, die sich nur in der Schreibung
    unterscheidet. Alles andere bleibt ein Befund fuer den Menschen."""
    geaendert = set()
    for p, alt, neu in m["reparabel"]:
        if any(a in p.parts for a in NIE_SCHREIBEN):
            print(f"AUSGELASSEN {p.relative_to(VAULT)}: Warteraum und Archiv werden nicht angefasst"); continue
        text = p.read_text(encoding="utf-8")
        muster = re.compile(r"\[\[(?:[^\]|#]*/)?" + re.escape(alt) + r"(?=[\]|#\\])")   # auch [[Ordner/Alte Notiz]]
        teile, stand = [], 0
        for code in CODE.finditer(text):                           # Code bleibt, wie er ist
            teile.append(muster.sub("[[" + neu, text[stand:code.start()])); teile.append(code.group(0)); stand = code.end()
        teile.append(muster.sub("[[" + neu, text[stand:]))
        if (neu_text := "".join(teile)) == text:
            continue
        p.write_text(neu_text, encoding="utf-8"); geaendert.add(p)
        print(f"REPARIERT {p.relative_to(VAULT)}: [[{alt}]] -> [[{neu}]]")
    if geaendert:
        pfade = [str(p.relative_to(VAULT)) for p in geaendert]
        subprocess.run(["git", "-C", str(VAULT), "add", "--", *pfade], check=True)
        subprocess.run(["git", "-C", str(VAULT), "commit", "-q", "-m", f"hygiene: Verweise in {len(pfade)} Datei(en) repariert", "--", *pfade], check=True)
        print(f"Commit: {len(pfade)} Dateien, nur diese")


def selbsttest():
    with tempfile.TemporaryDirectory() as d:
        pfad = pathlib.Path(d, "t.md")
        pfad.write_text("---\nattendees: [[Nicht Link]]\n---\n`[[kein Link]]`\n```\n[[auch nicht]]\n```\n"
                        "[[Alias\\|mit Pipe]] [[Normal|Alias]] [[Mit#Anker]] ![[bild.png]] [[Ordner/Tief]]\n", encoding="utf-8")
        (pathlib.Path(d) / "bild.png").write_bytes(b"x"); pathlib.Path(d, "Ordner").mkdir(); pathlib.Path(d, "Ordner", "Tief.md").write_text("x")
        ist = links(pfad.read_text())
        soll = ["Alias", "Normal", "Mit", "bild.png", "Ordner/Tief"]
        global VAULT; VAULT = pathlib.Path(d)
        tote = [z for _, z in messen()["tote"]]
        ok = ist == soll and tote == ["Alias", "Normal", "Mit"]
        print(f"Parser: {ist} == {soll}; tot nur {tote}: {'OK' if ok else 'FEHLER'}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reparieren", action="store_true"); ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        selbsttest()
    m = messen()
    print(f"{m['notizen']} Notizen: {len(m['tote'])} tote Verweise ({len(m['reparabel'])} reparabel), "
          f"{len(m['mehrdeutig'])} mehrdeutige, {len(m['ohne_source'])} ohne source, {len(m['verwaist'])} verwaist")
    for p, z in m["tote"]:
        print(f"  tot        {p.relative_to(VAULT)} -> [[{z}]]")
    for p, z in m["mehrdeutig"]:
        print(f"  mehrdeutig {p.relative_to(VAULT)} -> [[{z}]]")
    for p in m["ohne_source"]:
        print(f"  ohne source {p.relative_to(VAULT)}")
    for p in m["verwaist"]:
        print(f"  verwaist   {p.relative_to(VAULT)}")
    print(f"Zeitreihe: {zeitreihe(m).relative_to(VAULT)}")
    if a.reparieren:
        reparieren(m)
