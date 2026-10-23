#!/usr/bin/env bash
# Reihenfolge ist der Punkt: erst ins private Netz, nachweislich darueber anmelden,
# DANN den oeffentlichen SSH-Port schliessen. Umgekehrt sperrt man sich aus.
set -euo pipefail
tailscale up --hostname=wissen --accept-routes=false --ssh=false
echo "Jetzt in einem ZWEITEN Terminal pruefen: ssh arbeit@wissen  (ueber das Tailnet)."
read -r -p "Hat die Anmeldung ueber das Tailnet geklappt? (ja/nein) " ok
[ "$ok" = "ja" ] || { echo "Abbruch: Port bleibt offen, bis der Weg ueber das Netz steht."; exit 1; }
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0 to any port 22 proto tcp comment 'SSH nur ueber das Tailnet'
ufw --force enable
# Gegenprobe: eine ungebundene Regel auf 22 wuerde die gebundene aufheben, ohne sie zu entfernen
ufw status verbose | grep -E '^(22(/tcp)?|OpenSSH)( \(v6\))?\s+ALLOW IN\s+Anywhere' && { echo "ABBRUCH: Port 22 ungebunden offen"; exit 77; }
sysctl -w net.ipv4.ip_forward=0 >/dev/null
sysctl -w net.ipv6.conf.all.forwarding=0 >/dev/null
printf 'net.ipv4.ip_forward=0\nnet.ipv6.conf.all.forwarding=0\n' > /etc/sysctl.d/98-no-forward.conf
