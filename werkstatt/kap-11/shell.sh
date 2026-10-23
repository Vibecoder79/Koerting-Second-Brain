# einmal je Maschine, unter dem Konto, das pusht: Git holt sich den Zugang ueber den Helfer.
# Der Helfer braucht GITHUB_APP_ID (und GITHUB_APP_KEY, wenn der Schluessel nicht am Standardort liegt)
# in der Umgebung dieses Kontos, auch unter Cron; sonst bricht er mit «GITHUB_APP_ID fehlt» ab.
git config --global credential.https://github.com.helper "!/opt/plattform/github_zugang.py credential"
# Probe ohne Push: Git fragt den Helfer, als muesste es sich anmelden; das Kennwort ist der Stundenzugang und bleibt verdeckt
printf 'protocol=https\nhost=github.com\n' | git credential fill | sed 's/^password=.*/password=(verdeckt)/'
