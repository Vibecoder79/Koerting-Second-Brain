#!/usr/bin/env bash
# Probe fuer den Git-Riegel: Negativfaelle, Gegenproben, Fehlerfaelle.
set -uo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; R="$HIER/git-riegel.sh"; rot=0; n=0
lauf() { printf '{"tool_name":"Bash","tool_input":{"command":%s}}' "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1")" | bash "$R"; }
sperrt() { n=$((n+1)); local a; a=$(lauf "$1"); if printf '%s' "$a" | grep -q '"deny"'; then echo "  OK    sperrt: $1"; else echo "  FEHLT sperrt NICHT: $1"; rot=$((rot+1)); fi; }
laesst() { n=$((n+1)); local a; a=$(lauf "$1"); if [ -z "$a" ]; then echo "  OK    laesst durch: $1"; else echo "  FEHLT sperrt faelschlich: $1 ($a)"; rot=$((rot+1)); fi; }
echo "== verweigert =="
sperrt 'git add -A'
sperrt 'git add .'
sperrt "$(printf 'cd vault %s git add -A %s git commit -m x' '&&' '&&')"
sperrt 'git commit -m "docs: x"'
sperrt 'git push --force origin main'
sperrt 'git commit --amend --no-edit'
sperrt "$(printf 'git commit -m x %s git add -- f' '&&')"
sperrt 'rm "05 Daily Notes/2026-10-21.md"'
sperrt 'rm -rf /opt/vault/work/vault/06'
sperrt 'git -C /opt/vault/work/vault add -A'
sperrt 'git -C /opt/vault/work/vault commit -m x'
sperrt 'git commit --allow-empty -m x'
echo "== laesst durch (Gegenproben) =="
laesst 'git add -- "05 Daily Notes/2026-10-21.md" CLAUDE.md'
laesst 'git commit -q -m "docs: x" -- "05 Daily Notes/2026-10-21.md"'
laesst "$(printf 'git commit -m "$(cat <<MSG\nfeat: x\n\nZeile zwei\nMSG\n)" -- CLAUDE.md')"
laesst 'git commit --amend --no-edit -- CLAUDE.md'
laesst 'git push -u origin feat/x'
laesst 'git status --short'
laesst 'rm -rf /tmp/wegwerf'
laesst "$(printf 'git push origin main %s rm -f /tmp/a' '&&')"
laesst 'git -C /opt/vault/work/vault commit -m x -- f'
echo "== sichtbarer Fehlerfall =="
n=$((n+1)); a=$(printf '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | GIT_RIEGEL_MUSTER=/nirgends bash "$R")
if printf '%s' "$a" | grep -q 'INAKTIV'; then echo "  OK    ohne Musterdatei meldet er sich: $a"; else echo "  FEHLT schweigt ohne Musterdatei"; rot=$((rot+1)); fi
n=$((n+1)); a=$(printf 'kein json' | bash "$R"); if printf '%s' "$a" | grep -q 'INAKTIV'; then echo "  OK    kaputter Eingang gemeldet"; else echo "  FEHLT kaputter Eingang verschluckt"; rot=$((rot+1)); fi
M=$(mktemp); printf '(\t kaputtes Muster\n(^|[;&|]\\s*)git\\s+add\\s+-A\\b\tpauschal\n' > "$M"
n=$((n+1)); a=$(printf '{"tool_name":"Bash","tool_input":{"command":"git add -A"}}' | GIT_RIEGEL_MUSTER="$M" bash "$R"); rm -f "$M"; z=$(printf '%s' "$a" | grep -c '^{'); if [ "$z" -eq 1 ] && printf '%s' "$a" | grep -q '"deny"' && printf '%s' "$a" | grep -q 'kaputtes Muster'; then echo "  OK    kaputtes Muster und Treffer: ein JSON mit beidem"; else echo "  FEHLT kaputtes Muster ($z Objekte: $a)"; rot=$((rot+1)); fi
echo "$((n-rot)) von $n Faellen gruen"; exit $(( rot > 0 ))
