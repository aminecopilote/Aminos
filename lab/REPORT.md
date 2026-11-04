# Rapport d'essai — dépôts tiers et banc de notarisation

Date : 2026-10-14. Environnement : conteneur cloud Linux, Python 3.13, Node 22, accès réseau limité à PyPI, npm et GitHub.
Reproductible : `lab/vendor_test.sh` (commits épinglés, installation isolée sous `lab/vendor/`, `npm ci --ignore-scripts`).
Deux exécutions complètes depuis zéro ont donné les mêmes résultats.

## Les cinq dépôts demandés

| Dépôt (commit) | Résultat de ses propres tests | Utilité pour ce projet | Intégré ? |
|---|---|---|---|
| [SuperInstance/agent-coordinator](https://github.com/SuperInstance/agent-coordinator) (`4d2560d`) | **15 réussis, 2 échecs, 7 erreurs** (tests périmés : `AgentCoordinator(name=…)`, `TaskBuilder.with_capability` n'existent plus) | Moteur de rôles, file de tâches, agents. **Le README décrit une API synchrone qui n'existe pas** ; le code réel est asynchrone | **Oui** (`aminos/swarm.py`), voir défauts ci-dessous |
| [tools-for-agents/agent-hq](https://github.com/tools-for-agents/agent-hq) (`785cd8c`) | **62/62** | Tableau kanban + mémoire partagée + MCP pour agents. Pourrait suivre les dossiers | Non (testé seulement) |
| [ChristopheAI/reverseengineeranything](https://github.com/ChristopheAI/reverseengineeranything) (`9f3639f`) | **285/287** tests ; 12 fichiers en échec | Rétro-ingénierie de binaires (Hopper, macOS). **Sans rapport** avec la notarisation ou la traduction | Non |
| [zaibunnisa33/legal-translator](https://github.com/zaibunnisa33/legal-translator) (`69d2ed6`) | Pas de tests ; syntaxe et import vérifiés | Source d'inspiration du pipeline traduire → rétro-traduire → comparer → corriger, **déjà repris dans Aminos** (et dépassé : glossaires, contrôles déterministes, mémoire) | Déjà intégré avant |
| [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (`bd956db`) | 278 fichiers de personas lus, `divisions.json` valide | Prompts de personas généralistes. Le « Language Translator » est espagnol↔anglais courant ; leurs consignes (commentaires, adaptation culturelle) contredisent la règle « verbatim, sans commentaire » | Non, volontairement |

Échecs de REA : les 12 fichiers et 2 tests en échec viennent tous de `pty.node` (module natif non compilé), parce que les scripts
d'installation d'un code tiers ne sont pas exécutés. Ce n'est pas un défaut de REA, et sans effet sur ce projet.

### Défauts constatés dans agent-coordinator (et contournés dans Aminos)

1. **Pas de relance automatique** : une tâche en échec revient avec `success=False`, `max_retries` n'est pas utilisé. La boucle de reprise est écrite dans Aminos.
2. **Pas de vrai parallélisme par défaut** : un agent n'est marqué occupé que lorsque son worker démarre la tâche, donc une passe de répartition empile toutes les tâches sur le premier agent libre. Mesuré : 6 tâches de 0,3 s prennent 1,84 s (séquentiel). Contournement : un rôle et une capacité par traducteur, distribution circulaire → 1,2 s avec 3 agents (test `test_translators_really_run_in_parallel`). Pas de vol de tâches : un agent lent ralentit sa part.
3. Les gestionnaires s'exécutent dans la boucle asyncio : un appel LLM bloquant figerait tous les agents. Aminos les exécute via `asyncio.to_thread`.

## Ce qui a été construit et testé (51 tests, tous réussis dans une installation propre)

- **Mémoire de traduction** (`aminos/tm.py`) : index FTS5 à la place d'un balayage complet, migration automatique des anciennes bases, paires de langues quelconques.
- **Importeurs** (`aminos/corpus.py`) : TMX (balises en ligne ignorées, `.gz`, lecture en flux), Moses, TBX. Voir `lab/CORPORA.md`.
- **Notarisation locale** (`aminos/notary/`) : empreinte, registre chaîné, PKI d'essai (la clé de l'autorité est détruite après émission, clé du signataire en 0600), CMS détaché vérifié par OpenSSL, PDF signé/vérifié par pyHanko.
  Cas négatifs testés : document modifié, sceau d'une autre autorité, PDF altéré, entrée de registre modifiée / supprimée, extension d'une chaîne cassée refusée.
- **Agents** (`aminos/swarm.py`) : escalade normal → hard → fournisseur suivant, panne de fournisseur absorbée, seuls les blocs en échec relancés, mémoire réutilisée puis alimentée, échec final signalé comme tel, scellement uniquement d'une traduction conforme.

## Ce qui n'a PAS été fait ou testé

- **Aucun appel à un vrai modèle** : aucune clé de fournisseur dans l'environnement. Les agents sont testés avec des modèles factices ; la qualité de traduction réelle est inconnue.
- **Aucun corpus ONU/UE réel** (réseau bloqué, voir `lab/CORPORA.md`) ; performances à grande échelle non mesurées.
- **Aucune apostille ni ancrage blockchain** : le réseau NEM/Catapult est inaccessible d'ici, la bibliothèque LuxTag est dans votre dossier local `notarisation\` et n'est pas dans cette session, et son code date de 2019. Le registre chaîné fournit la preuve d'ordre et d'intégrité locale ; son empreinte de tête peut servir d'ancre ultérieure (courriel à un tiers, horodatage public).
- **Pas de pivot** ar→(fr|en)→nl.
- L'apostille de La Haye ne relève que de l'autorité compétente du pays émetteur ; rien ici ne la remplace, ni une signature qualifiée eIDAS.
