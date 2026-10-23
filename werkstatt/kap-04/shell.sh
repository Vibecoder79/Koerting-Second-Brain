sudo install -m 644 00-haertung.conf /etc/ssh/sshd_config.d/00-haertung.conf
sudo sshd -t                                   # ganze Konfiguration pruefen, kaputte Optionen werden genannt
sudo sshd -T | grep -iE 'permitrootlogin|passwordauthentication'   # der WIRKSAME Wert
echo 'ssh_pwauth: false' | sudo tee /etc/cloud/cloud.cfg.d/99-no-pwauth.cfg   # sonst schreibt cloud-init zurueck
sudo systemctl reload ssh
