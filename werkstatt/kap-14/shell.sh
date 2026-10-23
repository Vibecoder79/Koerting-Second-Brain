# Vier Notizen fuer die Probe der Messung, dazu zum Beispiel-Vault aus Kapitel 12: ein toter Verweis mit
# genau einem Ziel in anderer Schreibung, zwei Dateien mit demselben Namen, eine Notiz ohne source.
V="${VAULT_DIR:-/opt/vault/work/vault}"
mkdir -p "$V/03 Bereiche/Beispiel-Bereich" "$V/02 Projekte/Beispiel-Projekt/Meetings" "$V/04 Ressourcen"
printf -- '---\ntyp: bereich\nsource: eigner\n---\n# Beispiel-Bereich\n\nVerweis auf [[Beispielprojekt - Hub]], einen toten [[Alte Notiz]] und einen mehrdeutigen [[Protokoll]].\n' > "$V/03 Bereiche/Beispiel-Bereich/Beispiel-Bereich.md"
printf -- '---\ntyp: notiz\nsource: eigner\n---\n# alte notiz\n\nKleingeschrieben: das einzige Ziel fuer [[Alte Notiz]].\n' > "$V/04 Ressourcen/alte notiz.md"
printf -- '---\ntyp: meeting\nsource: transkriptionsdienst\nprovenance:\n  origin: ingested-external\n---\n# Protokoll\n\nMaterial.\n' > "$V/02 Projekte/Beispiel-Projekt/Meetings/Protokoll.md"
printf -- '---\ntyp: notiz\n---\n# Protokoll\n\nZweite Datei mit demselben Namen, und ohne source.\n' > "$V/03 Bereiche/Beispiel-Bereich/Protokoll.md"
