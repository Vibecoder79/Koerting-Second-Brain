#!/usr/bin/env bash
# Legt einen Werkzeug-Schluessel ab: Wert unsichtbar von der Tastatur bis Strg-D, Datei 0640 fuer die Lesegruppe.
# Nie aus einem Argument (stuende in der Shell-Historie), nie aus einer KI-Sitzung (stuende im Protokoll).
# Der Ordner gehoert dem Dienstkonto (Kapitel 4); der Eigner ruft das Skript deshalb mit sudo.
# Ein mehrzeiliger Schluessel (PEM) wird ganz gelesen; eine Zeile allein liesse den Rest in der Shell.
set -euo pipefail
ORDNER="${SECRETS_DIR:-/opt/vault/secrets}"
GRUPPE="${SECRETS_GRUPPE:-geheim}"
[ -n "${1:-}" ] || { echo "Aufruf: sudo schluessel_ablegen.sh <datei>; der Wert wird abgefragt, Ende mit Strg-D" >&2; exit 2; }
case "$1" in */*|.*) echo "ABBRUCH: ein Dateiname ohne Pfad und ohne fuehrenden Punkt" >&2; exit 2;; esac
ZIEL="$ORDNER/$1"
echo "Wert fuer $1 einfuegen (unsichtbar), dann Strg-D:" >&2
[ -t 0 ] && { stty -echo; trap "stty echo" EXIT; }
WERT="$(cat)"
[ -n "$WERT" ] || { echo "ABBRUCH: leerer Wert" >&2; exit 2; }
case "$(printf '%s' "$WERT" | tr -d '\n')" in
  *[[:cntrl:]]*) echo "ABBRUCH: Steuerzeichen im Wert; beim Einfuegen eine Pfeiltaste erwischt?" >&2; exit 2;;
esac
umask 027
printf '%s\n' "$WERT" > "$ZIEL.neu"
chgrp "$GRUPPE" "$ZIEL.neu" || { rm -f "$ZIEL.neu"; echo "ABBRUCH: Gruppe $GRUPPE nicht setzbar; so koennte der Job nicht lesen" >&2; exit 2; }
chmod 0640 "$ZIEL.neu"
mv "$ZIEL.neu" "$ZIEL"
echo "abgelegt: $ZIEL ($(stat -c '%a %U:%G' "$ZIEL"), $(wc -l < "$ZIEL") Zeile(n), $(wc -c < "$ZIEL") Byte)"
