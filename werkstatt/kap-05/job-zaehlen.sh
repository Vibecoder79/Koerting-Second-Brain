#!/usr/bin/env bash
# Der eigentliche Job: zaehlt Notizen je Baum und schreibt eine Tabelle ins Vault.
# Seine Grenze steht im Code: er schreibt genau eine Datei, unterhalb von VAULT_DIR.
set -euo pipefail
VAULT_DIR="${VAULT_DIR:-/opt/vault/work/vault}"
ZIEL="$VAULT_DIR/04 Ressourcen/Zaehlung.md"
cd "$VAULT_DIR"
{
  printf -- '---\ntyp: register\nsource: job-zaehlen\nerstellt: %s\n---\n# Notizen je Baum\n\n| Baum | Notizen |\n|---|---|\n' "$(date +%F)"
  for b in [0-9][0-9]\ */; do printf '| %s | %s |\n' "${b%/}" "$(find "$b" -name '*.md' | wc -l)"; done
} > "$ZIEL"
