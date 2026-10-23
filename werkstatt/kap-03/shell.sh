python3 werkzeuge/anlegen.py --name "Beispielprojekt" --kuerzel BSP               # Trockenlauf
python3 werkzeuge/anlegen.py --name "Beispielprojekt" --kuerzel BSP --ausfuehren
git add -- "00 Kontext/Vorlagen" werkzeuge "02 Projekte/Beispielprojekt"
git commit -m "feat: Vorlagen, Anlage-Werkzeug, erstes Projekt" -- \
           "00 Kontext/Vorlagen" werkzeuge "02 Projekte/Beispielprojekt"
