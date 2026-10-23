# Second Brain Bauplan

Wie ein Second Brain gebaut wird: ein Wissensspeicher aus Markdown-Dateien unter Git, ein eigener
Server, der ihn rund um die Uhr füllt und prüft, und Sprachmodelle, die in eng gezogenen Rollen
lesen, verdichten und Aufträge vorbereiten. Der Lehrgang folgt einem Referenzsystem, das seit
April 2026 im täglichen Betrieb läuft, und beschreibt es so, dass man es nachbauen kann.

## Was hier liegt

| Datei oder Ordner | Inhalt |
|---|---|
| `Second Brain Bauplan.html` | Der Lehrgang als eine Datei: Einführung, Voraussetzungen und Kosten, 16 Kapitel, Glossar, Use-Case-Katalog. Öffnet sich ohne Anmeldung im Browser. |
| `Second Brain Agentenbau.html` | Der vertiefende Lehrgang zu Kapitel 13: wie eine einzelne Stelle mit Sprachmodell geplant, gesichert, abgenommen und verbessert wird. |
| `werkstatt/` | Die Code-Beispiele aus den Werkstätten der Kapitel 1 bis 14 und 16, je Kapitel ein Ordner. `werkstatt/README.md` nennt zu jeder Datei ihren Prüfstatus. |

## Wie die Beispiele zu lesen sind

Jedes Kapitel endet mit einer Werkstatt: Ziel, was du brauchst, Schritte mit Code, eine Prüfung
und typische Fehler. Der Code hier ist derselbe wie im Lehrgang, nur als Dateien.

- **ausgeführt** heisst: Die Datei ist im Arbeitsordner der Bausitzung auf dem Referenzserver
  gelaufen, mit dem Ergebnis, das der Abschnitt «So prüfst du es» im Kapitel nennt.
- **Syntax geprüft** heisst: aus dem Code des Referenzsystems abgeleitet und mechanisch geprüft,
  aber nicht gegen einen echten Dienst gelaufen.

Fremde Dienste sind in den Werkstätten Attrappen oder Dateien mit Beispielantworten. Jede
Werkstatt sagt, was damit nicht gemessen ist. Pfade sind Beispiele und kommen aus
Umgebungsvariablen; Domains sind reservierte Beispieldomains.

## Was bewusst fehlt

Keine Personen, Kunden, Adressen, Domains, Rechnernamen oder Zugangsdaten. Das Sicherheitskapitel
beschreibt Mechanismen und Muster, keine offenen Schwachstellen und keine Berechtigungslisten des
Referenzsystems. Werkzeuge und Dienste sind beim Namen genannt, weil man sie für einen Nachbau
braucht; keiner davon ist eine Empfehlung gegen Alternativen.

## Herkunft

Dieses Repository wird aus der Quelle des Lehrgangs erzeugt und nie von Hand gepflegt. Jeder
Stand nennt in seiner Commit-Nachricht den Quell-Commit, aus dem er gebaut wurde. Vor jedem
Stand laufen ein Scanner für Geheimnisse und ein Namens-Scan, beide mit Gegenprobe gegen eine
bekannt positive Datei.

Die Zahlen im Lehrgang gelten für den Stand vom 17.10.2026. Das Referenzsystem ändert sich
laufend; die Prinzipien sind stabiler als die Zahlen.
