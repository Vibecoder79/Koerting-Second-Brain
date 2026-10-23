umask 002
git init --bare -b main --shared=group /opt/vault/repo/vault.git
git -C /opt/vault/repo/vault.git config receive.fsckObjects true
cp post-receive /opt/vault/repo/vault.git/hooks/post-receive && chmod +x /opt/vault/repo/vault.git/hooks/post-receive
git clone /opt/vault/repo/vault.git /opt/vault/work/vault          # die Arbeitskopie, das Original
git -C /opt/vault/work/vault config core.sharedRepository group
# erste Notiz in der Arbeitskopie anlegen, dann:
git -C /opt/vault/work/vault add -- Start.md
git -C /opt/vault/work/vault commit -m "feat: erste Notiz" -- Start.md
git -C /opt/vault/work/vault push origin main
