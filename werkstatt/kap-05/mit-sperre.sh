#!/usr/bin/env bash
# Zweite Huelle: nur einer schreibt ins Vault, und was er schreibt, committet er.
#   mit-sperre.sh -- <befehl...>
# flock, weil der Kernel die Sperre mit dem Prozess freigibt, auch nach kill -9.
set -uo pipefail
umask 002
SPERRE="${VAULT_LOCK:-/opt/vault/vault-schreiben.lock}"
WARTE_S="${VAULT_LOCK_WARTE:-900}"
VAULT_DIR="${VAULT_DIR:-/opt/vault/work/vault}"
[ "${1:-}" = "--" ] && shift

# 9<> statt 9>: ">" wuerde die Datei leeren, BEVOR die Sperre greift, und der Wartende
# loeschte den Eintrag genau des Jobs, auf den er wartet.
exec 9<>"$SPERRE"
if ! flock -w "$WARTE_S" 9; then
  echo "ABBRUCH: Sperre nach ${WARTE_S}s nicht bekommen, haelt: $(cat "$SPERRE")" >&2
  exit 75   # EX_TEMPFAIL: voruebergehend, der naechste Takt versucht es wieder
fi
printf 'pid=%s job=%s seit=%s\n' "$$" "${1##*/}" "$(date -Iseconds)" > "$SPERRE"

# Vor dem Lauf den Stand der Nabe holen, sonst committet der Job auf einem alten Stand
# und der Hook aus Kapitel 4 kann die Arbeitskopie danach nicht mehr nachziehen.
NABE=""; git -C "$VAULT_DIR" remote get-url origin >/dev/null 2>&1 && NABE=origin
if [ -n "$NABE" ] && ! git -C "$VAULT_DIR" pull -q --ff-only origin main; then
  echo "ABBRUCH: Arbeitskopie laesst sich nicht nachziehen; Job nicht gestartet." >&2
  : > "$SPERRE"; exit 76   # eigener Code: Sync gebrochen, nicht Sperre belegt
fi

# Marke fuer die Nachernte, eine Sekunde zurueck: Dateien aus derselben Sekunde zaehlen mit.
MARKE=$(mktemp); touch -d "1 second ago" "$MARKE"
"$@"; RC=$?

# Nachernte: genau die Dateien, die seit der Marke geaendert wurden. Nie pauschal.
cd "$VAULT_DIR" || exit "$RC"
NEU=(); FREMD=0
while IFS= read -r -d '' eintrag; do
  pfad="${eintrag:3}"                       # ab Spalte 4; davor stehen die Statusspalten
  [ -f "$pfad" ] || continue
  if [ "$pfad" -nt "$MARKE" ]; then NEU+=("$pfad"); else FREMD=$((FREMD + 1)); fi
done < <(git status --porcelain -z --untracked-files=all)
rm -f "$MARKE"
if [ "${#NEU[@]}" -gt 0 ]; then
  git add -- "${NEU[@]}"
  if git commit -q -m "chore(${1##*/}): ${#NEU[@]} Datei(en) nach der Laufmarke geaendert, ${FREMD} fremde(r) Pfad(e) unberuehrt" -- "${NEU[@]}"; then
    echo "Nachernte: ${#NEU[@]} Datei(en) committet, ${FREMD} fremde(r) Pfad(e) unberuehrt."
    if [ -n "$NABE" ]; then
      if git push -q origin main; then echo "Nachernte: gepusht."
      else echo "Nachernte: push fehlgeschlagen, Nabe und Arbeitskopie weichen ab." >&2; [ "$RC" -eq 0 ] && RC=74; fi
    fi
  else
    # Ein verweigerter Commit (etwa durch das Prueftor) darf nicht wie Erfolg aussehen:
    # die Ausgabe laege sonst unbemerkt offen, genau der Zustand, gegen den die Nachernte gebaut ist.
    # Die Pfade kommen aus dem Index, sonst naehme sie ein spaeterer Commit ohne Pfadangabe mit.
    git reset -q -- "${NEU[@]}"
    echo "Nachernte: commit verweigert, Ausgabe liegt offen." >&2
    [ "$RC" -eq 0 ] && RC=74
  fi
fi
: > "$SPERRE"
exit "$RC"
