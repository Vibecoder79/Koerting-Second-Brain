#!/usr/bin/env bash
# Aeusserste Huelle: fuehrt den Befehl aus und schreibt Erfolg ODER Fehlschlag.
#   lebenszeichen.sh <name> -- <befehl...>
# Ein Job, der nur bei Erfolg schreibt, sieht im Bericht aus wie einer, der nie lief.
set -uo pipefail
export PATH=/usr/local/bin:/usr/bin:/bin   # Cron kennt nur /usr/bin:/bin; was interaktiv da ist, fehlt sonst
umask 002   # zwei Konten schreiben dieselben Dateien; die Gruppe muss weiterschreiben koennen
STATE_DIR="${HEARTBEAT_DIR:-/opt/vault/heartbeats}"
NAME="${1:?Aufruf: lebenszeichen.sh <name> -- <befehl...>}"; shift
[ "${1:-}" = "--" ] && shift
mkdir -p "$STATE_DIR"
START=$(date +%s)
"$@"; RC=$?
STATUS=erfolg; [ "$RC" -eq 0 ] || STATUS=fehlschlag
printf 'zeit=%s\nstatus=%s\nrc=%s\ndauer_s=%s\n' "$(date -Iseconds)" "$STATUS" "$RC" "$(( $(date +%s) - START ))" > "$STATE_DIR/$NAME"
exit "$RC"
