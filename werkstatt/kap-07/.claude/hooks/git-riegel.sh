#!/usr/bin/env bash
# Git-Riegel, Huelle: prueft Vorbedingungen, reicht den Eingang an den Kern durch.
# Ein Hook, der bei einem Fehler still 0 liefert, taeuscht Schutz vor. Fehlt etwas, sagt er es.
set -uo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUSTER="${GIT_RIEGEL_MUSTER:-$HIER/git-riegel-muster.txt}"
command -v python3 >/dev/null 2>&1 || { printf '{"systemMessage":"GIT-RIEGEL: python3 fehlt, Riegel INAKTIV."}\n'; exit 0; }
[ -r "$HIER/git-riegel.py" ] || { printf '{"systemMessage":"GIT-RIEGEL: Kern git-riegel.py fehlt, Riegel INAKTIV."}\n'; exit 0; }
[ -r "$MUSTER" ] || { printf '{"systemMessage":"GIT-RIEGEL: Musterdatei fehlt (%s), Riegel INAKTIV."}\n' "$MUSTER"; exit 0; }
# stdin wird durchgereicht; ein Heredoc-Python wuerde den Eingang verschlucken
GIT_RIEGEL_MUSTER="$MUSTER" exec python3 "$HIER/git-riegel.py"
