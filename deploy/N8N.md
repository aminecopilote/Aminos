# Automatisation n8n : surveiller et piloter les services Aminos (installation directe, sans Docker)

[n8n](https://n8n.io) exécute des workflows planifiés ou déclenchés par un formulaire. Aminos livre cinq workflows prêts à l'emploi, testés contre un vrai n8n (version épinglée **2.46.4**), et une API à jetons limités pour qu'ils puissent parler aux services.

> **Licence** : n8n est « fair-code » (*Sustainable Use License*) : gratuit pour un usage interne, l'offrir comme service commercial à des tiers demande une licence n8n. Vérifiez qu'elle convient à votre usage.

## Les cinq workflows

| Workflow | Quand | Ce qu'il fait |
|---|---|---|
| **Surveillance des services** | toutes les 5 min | interroge `/erp/api/system/status` (application, back-office, espace disque, intégrité des journaux d'audit) ; alerte au **changement d'état** et rappelle chaque heure tant que ça dure ; message « rétabli » ensuite |
| **Sauvegarde nocturne** | 2 h 30 | `POST /erp/api/system/backup` : copie cohérente (API de sauvegarde SQLite + contrôle d'intégrité) des comptes, bases et journaux de chaque cabinet dans `backups/` (mode 0700, 14 copies gardées) ; alerte si échec |
| **Récapitulatif quotidien** | 8 h | dossiers en retard, factures échues, encours, via le tableau de bord du back-office |
| **Dossiers non concluants** | toutes les 15 min | signale une fois chaque dossier du superagent resté `non_concluant` (relecture nécessaire) |
| **Formulaire de demande** | webhook | `POST /webhook/aminos-demande` : valide, crée le client et le dossier dans le back-office ; protégé par un secret (en-tête `X-Aminos-Secret`) |

Les quatre premiers ont aussi un déclencheur manuel (« Lancer à la main »). Les alertes partent vers **votre** webhook (Slack, Mattermost, Discord, ntfy… : corps JSON avec `text`, `content` et `message`). Sans URL d'alerte, rien n'est envoyé.

## Ce que n8n peut et ne peut pas faire ici

- Trois jetons, jamais de mot de passe : **système** (état, sauvegarde, liste des dossiers : rien d'autre), **lecture** (cabinet `admin`), **écriture** (création et modification, **jamais de suppression**). Ils ne sont stockés que sous forme d'empreinte côté Aminos ; `aminos n8n prepare` les crée et les met dans les identifiants chiffrés de n8n.
- Les nœuds *Execute Command*, *Read/Write Files* et *Local File Trigger* sont désactivés : n8n ne peut pas lancer de commandes sur le serveur.
- **Pas de redémarrage automatique de services.** Un redémarrage exige des droits système que ces jetons n'ont pas, et un automate qui redémarre tout seul masque les vraies pannes. Les workflows alertent ; vous décidez.
- L'éditeur n8n n'est **jamais publié** : il écoute sur `127.0.0.1:5678`, on y accède par tunnel SSH (`ssh -L 5678:127.0.0.1:5678 utilisateur@serveur`, puis http://localhost:5678). Le premier visiteur crée le compte propriétaire : faites-le tout de suite. Seul `/webhook/*` passe par Caddy.

## Installer

| Cible | Commande |
|---|---|
| **Ubuntu natif** | `sudo bash install.sh --domain votre.domaine --n8n --alert-url https://…` (installe Node 24 depuis NodeSource, n8n, un service `aminos-n8n`) |
| **Windows Server** | `.\bootstrap.ps1 -Ref <ref> -Saas -Domain votre.domaine -N8n -AlertUrl https://…` (Node 24 portable vérifié par somme SHA-256, tâche planifiée `Aminos-N8n`) |

Les mises à jour gardent vos workflows et vos modifications ; `--n8n-reimport` (Ubuntu), `-N8nReimport` (Windows) ou les rechargent depuis le modèle et **écrasent vos modifications**.

Jetons à la main : `python -m aminos.erp token create --scope system --label ops` (affiché une seule fois), `token list`, `token revoke --id N`. Le secret du formulaire est dans `credentials.json` (lisible seulement par root / le compte du service).

## Sauvegarde d'n8n lui-même

Les identifiants n8n sont chiffrés avec une clé générée au premier démarrage (`config` dans le dossier de données n8n). Sauvegardez ce dossier **avec** sa clé, ailleurs que sur le serveur (`/var/lib/aminos/n8n` sous Ubuntu, `data\n8n` sous Windows). La sauvegarde nocturne d'Aminos couvre les données d'Aminos, pas n8n.

## Limites

- Testé : chaque workflow importé et exécuté dans n8n 2.46.4 contre le vrai back-office (alertes reçues, sauvegarde vérifiée, client et dossier créés par le webhook); installateurs Ubuntu et Windows en CI. Non testé : l'envoi vers un vrai Slack/Discord, la publication derrière un vrai nom de domaine, une charge réelle.
- Le webhook de formulaire est public (protégé par le secret) : mettez-le derrière un formulaire qui n'expose pas le secret au navigateur (appel depuis votre serveur web), sinon n'importe quel visiteur pourrait le copier.
- `npm install n8n` échoue avec EBADPLATFORM (dépendance optionnelle d'une autre plateforme déclarée comme obligatoire) : les installateurs utilisent `--force`, ce qui est sans effet sur les paquets de votre plateforme.
- Une seule instance n8n, sans file d'attente ni haute disponibilité.
