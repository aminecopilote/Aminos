# Aminos pour Windows (sans Docker)

1. Décompressez `aminos-windows.zip` sur le serveur (Windows 10/11 ou Server 2019+, 64 bits).
2. Ouvrez PowerShell **en administrateur** dans le dossier décompressé :
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\install.ps1                              # accès local : http://127.0.0.1:8501
   .\install.ps1 -Domain aminos.exemple.com   # accès public HTTPS + mot de passe (Caddy)
   ```
3. Le mot de passe (mode public) est affiché une fois et écrit dans `C:\Aminos\FIRST_PASSWORD.txt` : notez-le puis supprimez le fichier.

Le paquet contient toutes les dépendances Python (installation hors ligne, sommes de contrôle vérifiées). Il télécharge seulement
Python 3.12 (python.org) s'il est absent, et Caddy (GitHub, somme de contrôle vérifiée) en mode public.
Sans `-Domain`, l'application n'écoute que sur 127.0.0.1 : n'ouvrez jamais le port 8501 sur Internet, elle n'a pas de mot de passe propre.
Désinstallation : `C:\Aminos\uninstall.ps1` (`-DeleteData` pour effacer aussi la mémoire de traduction).
