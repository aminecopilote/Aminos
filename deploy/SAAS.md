# Aminos en SaaS multi-utilisateurs

`saas_app.py` ajoute à l'application une couche de comptes. Trois façons de la mettre en ligne :

| Cible | Commande | Modèle local possible ? |
|---|---|---|
| VPS Linux | `sudo bash deploy/install.sh --domain aminos.exemple.com --local-llm` (voir `DEPLOY.md`) | oui (Ollama) |
| VPS ou poste Windows | `.\install.ps1 -Saas -Domain aminos.exemple.com` (voir `windows/LISEZ-MOI.md`) | oui (Ollama pour Windows) |
| Render | bouton « New Blueprint » sur ce dépôt (fichier `render.yaml`) | **non** : traduction par un fournisseur tiers |

## Ce que la couche SaaS fait
- **Pas d'inscription publique** : l'administrateur crée les comptes (onglet *Administration*), mot de passe provisoire affiché une fois.
- **Mots de passe** : scrypt avec sel par compte, 12 caractères minimum. Après 5 échecs en 15 minutes, le compte refuse les connexions pendant 15 minutes (un attaquant qui connaît un identifiant peut donc le bloquer 15 minutes : compromis assumé). Message d'échec identique que le compte existe ou non.
- **Cabinets** : chaque cabinet a son dossier (`<AMINOS_DATA_DIR>/tenants/<cabinet>/`) avec sa mémoire de traduction et son journal. Le chemin ne vient jamais de l'utilisateur. Les membres d'un même cabinet partagent la mémoire.
- **Quotas par compte et par jour** (documents, caractères), contrôlés **avant** tout envoi à un modèle.
- **Journal d'audit par cabinet**, chaîné (toute modification, suppression ou réordonnancement est détecté) : qui, quoi, quand, empreinte SHA-256 du document. Jamais le texte.
- **Fournisseurs distants désactivés par défaut** : seul le modèle local `ollama` est proposé. Pour autoriser un tiers, deux verrous : `AMINOS_ALLOW_REMOTE_LLM=1` côté serveur, puis la case « fournisseurs distants » sur chaque compte. Les clés d'API sont celles du serveur, jamais saisies par les utilisateurs.
- Session expirée après 60 minutes d'inactivité (`AMINOS_SESSION_MINUTES`).

## Confidentialité : à lire avant d'y mettre de vraies pièces
- **Sur Render, le texte des documents part chez le fournisseur de modèle** (aucun modèle local possible). Pour des pièces soumises au secret professionnel, utilisez un VPS avec Ollama.
- La mémoire de traduction contient les phrases traduites de chaque cabinet : c'est une donnée aussi sensible que les pièces. Sauvegardez-la (`backup.sh`) et protégez le serveur.
- Hébergement, sous-traitants, durée de conservation, registre des traitements, mentions et conditions d'utilisation : à faire valider juridiquement (RGPD, secret professionnel). Rien de cela n'est fourni ici.

## Limites connues
- **Une seule instance** : SQLite sur disque. Ne pas faire monter à plusieurs instances.
- Pas de paiement ni d'abonnement, pas de SSO (Authelia ou Keycloak pourraient se placer devant plus tard), pas d'authentification à deux facteurs, pas de limitation par adresse IP (seulement par compte).
- Pas de reprise de mot de passe en libre-service : l'administrateur le réinitialise.
- Les téléversements ne sont pas conservés : traités dans un dossier temporaire puis supprimés.
- Testé : logique des comptes (quotas, verrouillage, isolation, audit) en tests automatiques ; écran de connexion, refus, onglet Administration et chaîne d'audit dans un vrai navigateur derrière Caddy ; la CI Windows teste l'authentification sur Windows. **Non testé** : `render.yaml` sur Render (non validable depuis ici), parcours complet d'une vraie traduction par un utilisateur (aucun modèle disponible dans les essais), charge à plusieurs utilisateurs simultanés.

## Render
1. Poussez ce dépôt sur votre compte GitHub, puis Render → *New* → *Blueprint*.
2. Renseignez `AMINOS_ADMIN_USER`, `AMINOS_ADMIN_PASSWORD` (12 caractères minimum) et la clé du fournisseur (`ANTHROPIC_API_KEY`).
3. Le disque persistant demande une formule payante. Région choisie : Francfort (modifiable dans `render.yaml`).
4. Ouvrez l'URL fournie, connectez-vous, créez les comptes, puis cochez « fournisseurs distants » pour ceux qui peuvent l'utiliser.
