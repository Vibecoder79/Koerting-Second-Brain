#!/usr/bin/env bash
# Eine App-Registrierung je Rolle, mit Anwendungszugang (kein Benutzer im Spiel) und dem
# kleinsten Recht fuer dieses Beispiel: Mail.ReadWrite, begrenzt durch eine Zugriffsrichtlinie
# auf EIN Postfach. Laeuft einmal, als Administrator des Mandanten, mit der Azure-CLI.
set -euo pipefail
APP=$(az ad app create --display-name "wissen-mail-entwurf" --query appId -o tsv)
az ad sp create --id "$APP" >/dev/null
GRAPH=00000003-0000-0000-c000-000000000000                      # Microsoft Graph
MAIL_RW=e2a3a72e-5f79-4c64-b1b1-878b674786c9                   # Rolle Mail.ReadWrite (Anwendung)
az ad app permission add --id "$APP" --api "$GRAPH" --api-permissions "$MAIL_RW=Role"
az ad app permission admin-consent --id "$APP"
# Das Geheimnis zeigt der Mensch sich in SEINEM Terminal an und legt es auf dem Server ab;
# dieser Schritt laeuft nie im Hintergrund einer KI-Sitzung (Kapitel 9, Lehre).
az ad app credential reset --id "$APP" --years 2 --query password -o tsv
echo "Danach im Mandanten: New-ApplicationAccessPolicy fuer $APP auf genau ein Postfach,"
echo "und Test-ApplicationAccessPolicy mit einem erlaubten UND einem fremden Postfach."
