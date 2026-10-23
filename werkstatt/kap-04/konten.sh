#!/usr/bin/env bash
# Drei Konten mit getrennten Aufgaben, eine Gruppe fuer das gemeinsame Verzeichnis.
# Laeuft einmal als root beim Aufbau. Namen sind Beispiele.
set -euo pipefail
groupadd --system vault
useradd --create-home --shell /bin/bash arbeit                 # Arbeitssitzungen, besitzt den Code
useradd --create-home --shell /bin/bash betrieb                # besitzt die Git-Ablage, nimmt Pushes an
useradd --system --shell /usr/sbin/nologin --no-create-home jobs   # faehrt Jobs, kann sich nicht anmelden
usermod -aG vault arbeit; usermod -aG vault betrieb; usermod -aG vault jobs
# setgid (das fuehrende 2): neue Dateien und Ordner erben die Gruppe
install -d -m 2775 -o betrieb -g vault /opt/vault
install -d -m 2775 -o betrieb -g vault /opt/vault/repo /opt/vault/work /opt/vault/heartbeats /opt/vault/logs
# setgid regelt nur den Besitzer: Jedes Skript, das hier schreibt, setzt umask 002, und die
# Git-Ablagen bekommen core.sharedRepository=group (Schritt 4).
# Git weigert sich seit 2.35.2, in einer Ablage zu arbeiten, die einem anderen Konto gehoert
# («dubious ownership»). Der Job laeuft als jobs, die Ablage gehoert betrieb: deshalb systemweit freigeben.
git config --system --add safe.directory /opt/vault/work/vault
git config --system --add safe.directory /opt/vault/repo/vault.git
# Plattform-Code: alle lesen und ausfuehren, nur das Arbeitskonto schreibt
install -d -m 2755 -o arbeit -g vault /opt/plattform
# Schluessel: eigenes Verzeichnis, eigene Lesegruppe aus genau zwei Konten
groupadd --system geheim; usermod -aG geheim arbeit; usermod -aG geheim jobs
install -d -m 2750 -o jobs -g geheim /opt/vault/secrets
