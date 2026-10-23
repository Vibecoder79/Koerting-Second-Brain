git init -b main vault && cd vault
mkdir -p "00 Kontext/Vorlagen" "01 Inbox" "02 Projekte" "03 Bereiche" \
         "04 Ressourcen" "05 Daily Notes" "06 Archiv" "08 Meeting Inbox"
for d in "02 Projekte" "03 Bereiche" "04 Ressourcen" "05 Daily Notes" "06 Archiv" "08 Meeting Inbox"; do
  : > "$d/.gitkeep"
done
