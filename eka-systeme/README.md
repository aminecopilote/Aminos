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
npm run dev      # http://localhost:5173
npm test         # tests Vitest + Testing Library
npm run build    # sortie dans dist/
```

Compte de démonstration (prérempli sur l’écran de connexion) : `k.berrada@atlas-negoce.ma` / `demo2026`.

## Ce qui est simulé

- **Authentification** : `src/data/api.js` accepte un seul compte et garde la session dans `sessionStorage`. Aucun jeton, aucun serveur.
- **Données** : toutes les données client (dossiers, échéances, paie, documents, activité) viennent de `src/data/mock.js`, figées au 17/10/2026.
- **Formulaire de contact** : validé côté client uniquement, la demande n’est envoyée nulle part.
- **Téléchargements, recherche et notifications** de l’espace client : affichés mais sans action.

Les écrans ne lisent jamais `mock.js` directement : ils passent par les fonctions asynchrones de `src/data/api.js`
(`login`, `logout`, `getSession`, `getDossiers`, `getDossier`, `getEcheances`, `getPaie`, `getDocuments`, `getActivite`).
Brancher un backend revient à réécrire le corps de ces fonctions en gardant leurs signatures.

## Déploiement

L’app utilise des URL propres (`BrowserRouter`) : le serveur doit renvoyer `index.html` pour toute route inconnue
(règle de réécriture SPA). Pour un déploiement dans un sous-dossier, construire avec `vite build --base=/sous-dossier/`.
