#!/usr/bin/env bash
# Soll (jobs.tsv) gegen Ist (Lebenszeichen). Kein Job im Register, kein Job im Bericht.
set -uo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${HEARTBEAT_DIR:-/opt/vault/heartbeats}"
[ -d "$STATE_DIR" ] || { echo "ABBRUCH: $STATE_DIR fehlt; sonst hiesse jeder Job 'nie gelaufen'" >&2; exit 78; }
JETZT=$(date +%s); problem=0
while IFS=$'\t' read -r name max takt _rest; do
  case "$name" in ''|'#'*|name) continue;; esac
  datei="$STATE_DIR/$name"
  if [ ! -f "$datei" ]; then echo "NIE   $name ($takt)"; problem=$((problem+1)); continue; fi
  status=$(grep -m1 '^status=' "$datei" | cut -d= -f2); rc=$(grep -m1 '^rc=' "$datei" | cut -d= -f2)
  zeit=$(grep -m1 '^zeit=' "$datei" | cut -d= -f2-); alter_h=$(( (JETZT - $(date -d "$zeit" +%s)) / 3600 ))
  if [ "$status" != erfolg ]; then echo "ROT   $name: fehlgeschlagen, rc=$rc"; problem=$((problem+1))
  elif [ "$alter_h" -gt "$max" ]; then echo "GELB  $name: ${alter_h} h alt, erlaubt ${max} h"; problem=$((problem+1))
  else echo "OK    $name: vor ${alter_h} h"; fi
done < "$HIER/jobs.tsv"
[ "$problem" -eq 0 ] && echo "Alle Jobs im Takt." || { echo "$problem Job(s) brauchen Aufmerksamkeit."; exit 77; }
