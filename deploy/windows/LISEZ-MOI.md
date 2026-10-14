# Aminos pour Windows (sans Docker)

1. Décompressez `aminos-windows.zip` sur le serveur (Windows 10/11 ou Server 2019+, 64 bits).
2. Ouvrez PowerShell **en administrateur** dans le dossier décompressé :
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\install.ps1                              # accès local : http://127.0.0.1:8501
   .\install.ps1 -Domain aminos.exemple.com   # accès public HTTPS + mot de passe (Caddy)
   ```
   .\install.ps1 -Saas -Domain aminos.exemple.com   # multi-utilisateurs : comptes, un dossier par cabinet, quotas, audit
3. Un raccourci **Aminos** est créé sur le Bureau (il démarre le service si besoin puis ouvre le navigateur).
4. Le mot de passe (mode public ou `-Saas`) est affiché une fois et écrit dans `C:\Aminos\FIRST_PASSWORD.txt` : notez-le puis supprimez le fichier.

Le paquet contient toutes les dépendances Python (installation hors ligne, sommes de contrôle vérifiées). Il télécharge seulement
Python 3.12 (python.org) s'il est absent, et Caddy (GitHub, somme de contrôle vérifiée) en mode public.
Sans `-Domain`, l'application n'écoute que sur 127.0.0.1 : n'ouvrez jamais le port 8501 sur Internet, elle n'a pas de mot de passe propre.
Mode `-Saas` : identifiant `admin`, puis créez les comptes dans l'onglet *Administration* (voir `deploy/SAAS.md` : confidentialité et limites).
Désinstallation : `C:\Aminos\uninstall.ps1` (`-DeleteData` pour effacer aussi la mémoire de traduction).

## Options supplémentaires
```powershell
.\install.ps1 -Saas -Orchestrator -Agency      # + supervision de la machine toutes les 5 min + copies locales agent-hq / agent-coordinator
.\install.ps1 -Skills chatgpt-skills:document-converter-suite   # + un skill tiers (texte seul, version épinglée)
.\update.ps1                                    # nouveau paquet sur une installation existante : données, mots de passe et options conservés
```
- **Orchestrateur** : un cycle JSON toutes les 5 minutes dans `C:\orchestrator\logs\orch-<date>.jsonl`. Les actions (redémarrage d'un service ou d'un conteneur) sont **seulement proposées** ; `aminos orchestrate --execute` n'exécute que celles de la liste blanche. Voir `skills\aminos\orchestrateur-central\SKILL.md`.
- **Chef d'agence** : `agency\AGENTS.md`. agent-hq (tableau kanban + mémoire d'agents) demande **Node 22** et n'écoute que sur `127.0.0.1:7700` : il n'a **aucune authentification**, ne l'exposez jamais.
- **Skills tiers** : `aminos skills available|install|verify|update|search`. Ils ne sont pas audités : relisez-les avant usage. `chatgpt-skills` n'a pas de licence déclarée, d'où une installation chez vous et non dans le paquet.

## Installation en une commande (en ligne)
PowerShell **en administrateur**, sur un serveur qui a accès à github.com, pypi.org et python.org. Remplacez `<COMMIT>` par la version à installer
(un identifiant de commit est immuable ; un nom de branche peut changer) :
```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr https://raw.githubusercontent.com/aminecopilote/Aminos/<COMMIT>/deploy/windows/bootstrap.ps1 -OutFile $env:TEMP\aminos-bootstrap.ps1
& $env:TEMP\aminos-bootstrap.ps1 -Ref <COMMIT> -Saas
```
Les options sont les mêmes que `install.ps1` (`-Domain`, `-Orchestrator`, `-Agency`, `-Skills`). Le script est téléchargé puis exécuté en deux temps pour que vous
puissiez le relire avant (`notepad $env:TEMP\aminos-bootstrap.ps1`). Mise à jour : `C:\Aminos\update.ps1 -Ref <nouveau commit>`.
Différence avec le paquet hors ligne : les dépendances viennent de PyPI au moment de l'installation, sans les sommes de contrôle du paquet.
