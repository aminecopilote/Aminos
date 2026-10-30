# EKA CONSEIL — site vitrine et espace client EKA SYSTÈME

Application React 18 + Vite 5 + Tailwind CSS 3, routée avec React Router 6.

| Route | Écran |
| --- | --- |
| `/` | Site vitrine EKA CONSEIL (services, valeur ajoutée, méthode, FAQ, contact) |
| `/espace-client/connexion` | Connexion à l’espace client (simulée) |
| `/espace-client` | Tableau de bord |
| `/espace-client/dossiers` | Liste des dossiers |
| `/espace-client/dossiers/:id` | Détail d’un dossier : étapes, avancement, pièces |
| `/espace-client/echeancier` | Échéancier réglementaire |
| `/espace-client/paie` | Paie & RH |
| `/espace-client/documents` | Coffre-fort documentaire |

## Démarrer

```bash
cd eka-systeme
npm ci
npm run dev      # http://localhost:5173 (données en mémoire)
npm run api      # API de démonstration (voir plus bas)
npm run dev:http # espace client branché sur cette API
npm test         # tests Vitest + Testing Library
npm run build    # sortie dans dist/
```

Compte de démonstration (prérempli sur l’écran de connexion) : `k.berrada@atlas-negoce.ma` / `demo2026`.

## Couche de données et backend

Les écrans ne lisent jamais `mock.js` directement : ils passent par les fonctions asynchrones de `src/data/api.js`
(`login`, `logout`, `getSession`, `getDossiers`, `getDossier`, `getEcheances`, `getPaie`, `getDocuments`, `getActivite`).
`api.js` délègue à un **adaptateur** choisi par la variable `VITE_EKA_API` :

| `VITE_EKA_API` | Adaptateur | Source des données |
| --- | --- | --- |
| `mock` (défaut) | `src/data/adaptateurs/mock.js` | `src/data/mock.js` en mémoire, aucun réseau |
| `http` | `src/data/adaptateurs/http.js` | API REST à l’adresse `VITE_EKA_API_URL` |

Le contrat de données (formes des objets et interface `Adaptateur`) est décrit en JSDoc dans `src/data/types.js`.

### Lancer l’espace client sur l’API de démonstration

```bash
npm run api        # serveur Node sans dépendance, http://127.0.0.1:8787/api
npm run dev:http   # dans un 2e terminal : Vite en mode http, /api relayé vers le serveur
```

`server/serveur.js` sert les données de `mock.js` derrière une vraie authentification par jeton :
sessions en mémoire (perdues au redémarrage), jeton aléatoire de 256 bits, expiration configurable.

### Contrat REST

Toutes les routes sont sous `VITE_EKA_API_URL` (par défaut `/api`). Sauf la connexion, elles exigent
l’en-tête `Authorization: Bearer <jeton>` et répondent `401 {"erreur": "..."}` sans jeton valide.

| Méthode | Route | Réponse |
| --- | --- | --- |
| `POST` | `/auth/connexion` corps `{email, motDePasse}` | `200 {jeton, client}` ou `401` |
| `POST` | `/auth/deconnexion` | `204` |
| `GET` | `/auth/session` | `Client` |
| `GET` | `/dossiers` | `Dossier[]` |
| `GET` | `/dossiers/:id` | `Dossier` ou `404` |
| `GET` | `/echeances` | `Echeance[]` |
| `GET` | `/paie` | `Paie` |
| `GET` | `/documents` | `Documents` |
| `GET` | `/activite` | `Activite[]` |

Côté front, un `401` efface le jeton (la session est perdue), un `404` sur un dossier renvoie `null`,
et une panne réseau lève une `ErreurApi` de statut `0`.

### Variables d’environnement

Voir `.env.example` (copier en `.env.local`, ignoré par Git). `.env.http` est chargé par `npm run dev:http`.

| Variable | Lue par | Défaut | Rôle |
| --- | --- | --- | --- |
| `VITE_EKA_API` | Vite (au build) | `mock` | `mock` ou `http` |
| `VITE_EKA_API_URL` | Vite (au build) | `/api` | Adresse de l’API en mode `http` |
| `EKA_API_PORT` | serveur et proxy Vite | `8787` | Port du serveur de démonstration |
| `EKA_API_HOST` | serveur | `127.0.0.1` | Interface d’écoute |
| `EKA_API_CORS_ORIGIN` | serveur | vide | Origine autorisée si le front est servi ailleurs (ex. `http://localhost:5173`) |
| `EKA_API_SESSION_MIN` | serveur | `120` | Durée de vie d’une session, en minutes |

### Brancher un vrai backend

- **API du cabinet** : implémenter les routes ci-dessus, puis builder avec `VITE_EKA_API=http` et
  `VITE_EKA_API_URL=https://api.exemple.ma/api`. Aucun changement de code front.
- **Autre fournisseur** (Supabase, Firebase…) : écrire `src/data/adaptateurs/<nom>.js` qui renvoie un objet
  conforme à `Adaptateur`, et l’ajouter dans `creerAdaptateur` de `api.js`. `src/test/backend.test.js`
  compare déjà l’adaptateur HTTP au mock ; en faire autant pour le nouveau.

### Ce qui reste simulé

- **Données** : figées au 17/10/2026, un seul client et un seul compte (`COMPTES` dans `server/serveur.js`).
- **Formulaire de contact** : validé côté client uniquement, la demande n’est envoyée nulle part.
- **Téléchargements, recherche et notifications** de l’espace client : affichés mais sans action.
- **Expiration en cours de navigation** : une session expirée fait échouer le chargement des écrans
  sans renvoyer automatiquement vers la connexion ; recharger la page y ramène.

## Déploiement

L’app utilise des URL propres (`BrowserRouter`) : le serveur doit renvoyer `index.html` pour toute route inconnue
(règle de réécriture SPA). Pour un déploiement dans un sous-dossier, construire avec `vite build --base=/sous-dossier/`.
