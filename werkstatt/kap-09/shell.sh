printf 'TENANT_ID=00000000-0000-0000-0000-000000000000\nCLIENT_ID=11111111-1111-1111-1111-111111111111\nCLIENT_SECRET=attrappe-ohne-geheimnis\n' > secrets/mail.env
ATTRAPPE_ROLLEN="Mail.ReadWrite" python3 attrappe_graph.py 18765 & ATTRAPPE_PID=$!
export GRAPH_LOGIN=http://127.0.0.1:18765 GRAPH_BASIS=http://127.0.0.1:18765/v1.0 GRAPH_ZUGANG=secrets/mail.env
python3 mail_entwurf.py --an "Muster Anna" --betreff "Inventar November" --text "Bitte die Liste bis 10.11."
python3 mail_entwurf.py --an "Muster Anna" --betreff "Inventar November" --text "Bitte die Liste bis 10.11." --ausfuehren
python3 riegel_probe.py
python3 rechte_waechter.py
kill "$ATTRAPPE_PID"
