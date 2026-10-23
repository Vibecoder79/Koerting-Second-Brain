# Koerting-Second-Brain

> Projekt-Regelwerk für Codex. Die Zwillingsdatei `CLAUDE.md` trägt dasselbe für Claude
> Code. Wer hier eine Regel ändert, ändert sie dort mit.

## Wo die Umgebung steht

**Infrastruktur, Zugänge und die Wege zum Ausrollen stehen nicht in diesem Repository.**
Die Quelle ist die «Umgebung — Landkarte» im Second Brain: welche Maschinen es gibt, welche
Dienste, welche Zugänge und welche Werkzeuge. Auf der Entwicklungsmaschine `development`
liegt sie gespiegelt unter `~/umgebung/`. **Lies sie, bevor du etwas ausrollst oder einen
Zugang brauchst.** Codex kennt keinen Import, der sie von selbst lädt.

Schlüssel gehören nie in dieses Repository, auch nicht in eine eingecheckte `.env`. Schlüssel
einer laufenden Anwendung setzt der Eigner in der Konsole des Hosters (Coolify oder Vercel).

## Was dieses Repository trägt

| Ordner | Wofür |
|---|---|
| `Decisions/` | Entscheidungen, eine Datei je Entscheid |
| `Journal/` | Arbeitsprotokoll je Sitzung: was gemessen, gebaut, offen ist |
| `Research/` | Recherchen zum Projekt |

Diese drei Ordner sind für den Rückweg ins Second Brain vorgesehen. Der Job, der sie
dorthin zieht, ist noch nicht gebaut.

## Git

- `main` ist geschützt. Gearbeitet wird auf einem Zweig, zusammengeführt per Pull Request,
  **und den Merge macht der Eigner**
- Gezielt adden: `git add -- <pfad>`, nie `git add -A`
- Nach dem Öffnen eines Pull Requests keine weiteren Commits auf denselben Zweig
