#!/usr/bin/env bash
# Haertung messen, taeglich, lokal. Sollwerte stehen hier im Skript.
#   0  alles eingehalten        77  Abweichung        78  nicht messbar
# Fehlt sudo oder antwortet ein Dienst nicht, ist das 78; ungemessen zaehlt als offen.
# SSHD_T und UFW_STATUS sind fuer die Probe ueberschreibbar.
set -uo pipefail
SSHD_T="${SSHD_T:-sudo -n sshd -T}"
UFW_STATUS="${UFW_STATUS:-sudo -n ufw status}"
rc=0
abweichung() { echo "ABWEICHUNG: $1"; rc=77; }
unmessbar()  { echo "NICHT MESSBAR: $1"; [ "$rc" -eq 77 ] || rc=78; }

# 1. SSH: der wirksame Wert laut laufendem Dienst
if ! wirksam=$($SSHD_T 2>/dev/null); then
  unmessbar "sshd -T liefert nichts (sudo ohne Passwort fuer diesen Befehl noetig)"
else
  for soll in "permitrootlogin no" "passwordauthentication no" "pubkeyauthentication yes"; do
    ist=$(printf '%s\n' "$wirksam" | grep -i "^${soll%% *} " | head -1)
    [ -z "$ist" ] && { unmessbar "sshd kennt ${soll%% *} nicht"; continue; }
    [ "$(printf '%s' "$ist" | tr 'A-Z' 'a-z')" = "$soll" ] || abweichung "sshd: $ist, soll: $soll"
  done
fi

# 2. Firewall: Port 22 nur auf dem Tailnet-Interface, und keine zweite, ungebundene Regel
if ! regeln=$($UFW_STATUS 2>/dev/null); then
  unmessbar "ufw status liefert nichts"
else
  printf '%s\n' "$regeln" | grep -q 'Status: active' || abweichung "ufw nicht aktiv"
  printf '%s\n' "$regeln" | grep -Eq '^22(/tcp)? on tailscale0\s+ALLOW' || abweichung "keine SSH-Regel auf tailscale0"
  # auch das Profil «OpenSSH» und die v6-Zeile sind ungebundene Regeln auf Port 22
  printf '%s\n' "$regeln" | grep -Eq '^(22(/tcp)?|OpenSSH)( \(v6\))?\s+ALLOW' && abweichung "Port 22 ungebunden offen"
fi

case $rc in 0) echo "OK: Haertung eingehalten";; 77) echo "ROT: Abweichung";; 78) echo "GELB: nicht vollstaendig gemessen";; esac
exit $rc
