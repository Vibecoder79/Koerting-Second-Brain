mkdir -p /opt/vault/work/vault/.githooks
cp pre-commit /opt/vault/work/vault/.githooks/pre-commit && chmod +x /opt/vault/work/vault/.githooks/pre-commit
git -C /opt/vault/work/vault config core.hooksPath .githooks
git -C /opt/vault/work/vault add -- .githooks
git -C /opt/vault/work/vault commit -m "feat: Prueftor" -- .githooks
git -C /opt/vault/work/vault push origin main
