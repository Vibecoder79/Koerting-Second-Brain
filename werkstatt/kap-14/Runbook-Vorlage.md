---
typ: runbook
status: aktiv
source: eigner
zuletzt_gebraucht: YYYY-MM-DD
---

# Runbook <Ablauf>

> Wofuer: <der seltene, kritische Ablauf in einem Satz>. Wann: <der Anlass, an dem man ihn braucht>.
> Zuletzt gebraucht und nachgefuehrt: siehe Datenkopf. Ein Pruefschritt, der beim Gebrauch falsch
> alarmiert, wird sofort korrigiert, nicht umgangen.

## Vorher messen

Jede Zeile ist ein Befehl mit dem erwarteten Ergebnis. Ein Nein beweist nur etwas, wenn derselbe
Befehl gegen einen bekannt positiven Fall angeschlagen hat.

| Was | Befehl | Erwartet | Referenz fuer ein Nein |
|---|---|---|---|
| <Zustand> | `<befehl>` | <Ausgabe> | `<derselbe Befehl gegen ein Ziel, das antwortet>` |

## Fenster

<Wann der Ablauf laufen darf und wann nicht; welche Jobs er unterbricht.>

## Schritte

1. <Schritt.> Pruefung: `<befehl>` zeigt <Ergebnis>.
2. <Schritt.> Pruefung: …
3. <Schritt.> Pruefung: …

## Nachher

`startprobe.py startprobe.tsv` loest jeden wichtigen Dienst aus. Drei Ergebnisse: OK, FEHLER,
UNGEPRUEFT. Ungeprueft zaehlt nie als gruen; der Ablauf ist erst fertig, wenn jede Zeile OK ist
oder ein Mensch die ungepruefte Zeile angesehen hat.

## Rueckweg

<Was tun, wenn ein Schritt scheitert: Konsole des Anbieters, zweite Sitzung, alter Stand.>

## Nachfuehren

Beim Gebrauch: Datum im Datenkopf, geaenderte Schritte, falsche Alarme. Das Datum steht hier von Hand,
obwohl Git Aenderungen kennt: Git weiss, wann die Datei geaendert wurde, nicht, wann der Ablauf lief. Ein Runbook, das seit
einem Jahr niemand gebraucht hat, ist ein Runbook, dem man nicht trauen sollte.
