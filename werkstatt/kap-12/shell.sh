# Beispiel-Notizen fuer die Probe: Aufgaben in der Inbox und ein Hub mit Kuerzel, im Vault aus Kapitel 3.
# Die Felder prioritaet, wartet_auf und art kommen zum Schema aus Kapitel 2 dazu (alle optional).
# Der Hub entsteht nur, wenn das Kuerzel noch nicht vergeben ist; im Vault aus Kapitel 3 traegt es schon ein Hub.
V="${VAULT_DIR:-/opt/vault/work/vault}"
mkdir -p "$V/01 Inbox" "$V/02 Projekte/Beispielprojekt"
grep -rlq '^meeting_key: BSP$' "$V" 2>/dev/null || printf -- '---\ntyp: projekt-hub\nmeeting_key: BSP\nstatus: aktiv\nstart: 2026-10-01\nende: offen\nsource: eigner\n---\n# Beispielprojekt\n' > "$V/02 Projekte/Beispielprojekt/Beispielprojekt - Hub.md"
printf -- '---\ntyp: aufgabe\nstatus: offen\nfaellig: 2026-10-19\nprioritaet: wichtig\nsource: eigner\n---\n# Angebot nachfassen\n' > "$V/01 Inbox/Angebot nachfassen.md"
printf -- '---\ntyp: aufgabe\nstatus: offen\nfaellig: 2026-10-22\nprioritaet: dringend\nsource: eigner\n---\n# Rechnung pruefen\n' > "$V/01 Inbox/Rechnung pruefen.md"
printf -- '---\ntyp: aufgabe\nstatus: offen\nfaellig: 2026-10-27\nprioritaet: wichtig\nsource: eigner\n---\n# Vortrag vorbereiten\n' > "$V/01 Inbox/Vortrag vorbereiten.md"
printf -- '---\ntyp: aufgabe\nstatus: offen\nfaellig: 2026-10-24\nwartet_auf: Antwort des Lieferanten seit 2026-10-15\nsource: eigner\n---\n# Lieferantenantwort einholen\n' > "$V/01 Inbox/Lieferantenantwort einholen.md"
printf -- '---\ntyp: aufgabe\nstatus: offen\nsource: eigner\n---\n# Lesezeichen sortieren\n' > "$V/01 Inbox/Lesezeichen sortieren.md"
printf -- '---\ntyp: aufgabe\nstatus: erledigt\nfaellig: 2026-10-20\nsource: eigner\n---\n# Schon erledigt\n' > "$V/01 Inbox/Schon erledigt.md"
