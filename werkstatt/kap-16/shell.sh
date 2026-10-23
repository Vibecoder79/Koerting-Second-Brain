git init -b main plattform && cd plattform
mkdir -p githooks tests
# Datei githooks/pre-commit wie oben anlegen, dann:
chmod +x githooks/pre-commit
git config core.hooksPath githooks
