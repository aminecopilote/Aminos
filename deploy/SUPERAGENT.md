# Superagent Aminos : traduction, certification, apostille, back-office

Un seul serveur, trois entrées : l'application de traduction et le **superagent** (`/`), le **back-office** (`/erp/`) et la ligne de commande (`aminos superagent …`). Mêmes comptes, un dossier de données par cabinet.

## Ce que fait le superagent

Un dossier de travail reprenable, en trois phases. Chaque phase s'enregistre : une coupure ou une relance reprend où l'on en était.

1. **`run`** : extraction → mémoire de traduction et glossaires → traduction avec escalade (mode normal, puis `hard` avec rétro-traduction, puis le fournisseur suivant) → contrôles (nombres, terminologie, segments vides) → brouillon `.docx` et table de relecture. Les seuls blocs non conformes sont relancés. Quand l'échelle est épuisée, le dossier est **`non_concluant`** avec la liste des points restants : jamais présenté comme réussi.
2. **`certify`** : après **relecture humaine** (`--reviewed-by` obligatoire). Page de certification (fr/en/nl/ar), cachet, pied de page « conforme à l'original » sur chaque page (si LibreOffice est installé), signature numérique PAdES visible, signature détachée du `.docx`, empreintes, entrée dans le registre chaîné.
3. **`dossier`** : assemble pièces, manifeste, liste de contrôle d'apostille. Il **n'émet pas** d'apostille.

```bash
aminos superagent init
aminos superagent set translator '{"name":"Prénom NOM","capacity":"traducteur assermenté près la cour d'appel de …","registration":"n° …","place":"Casablanca"}'
aminos superagent run acte.pdf -s arabe -t français -p ollama --tm tm.sqlite -g glossaire.json
aminos superagent certify <id-du-dossier> --reviewed-by "Prénom NOM"
aminos superagent verify <id>
aminos superagent dossier <id> --from MA --to FR --kind "acte d'état civil"
aminos superagent apostille-register <id> apostille-recue.pdf    # après dépôt à l'autorité compétente
aminos superagent selftest                                       # essai complet avec modèle factice
```

## Mémoire, instructions, compétences, paramètres

Un **profil** (dossier `superagent-profile/`, ou `…/tenants/<cabinet>/profile` en mode multi-utilisateurs) contient `instructions.md` (règles injectées dans chaque prompt, initialisées avec le style de traduction juridique), `params.json`, une mémoire interrogeable (SQLite FTS5) dont les notes pertinentes sont ajoutées au prompt, et des skills texte.

**Compte Claude** : un serveur ne peut pas lire un compte Claude. Exportez vous-même vos instructions (`CLAUDE.md`), vos notes de mémoire et vos dossiers de skills, puis :

```bash
aminos superagent import ./mon-export          # dossier ou fichier ; ou onglet « Profil et mémoire » (fichiers ou .zip)
```

Sont importés : instructions, notes (un paragraphe ou une puce = une note), skills (texte seul). **Jamais** : les scripts (listés comme ignorés), les conversations (`conversations.json`). Les skills tiers restent sous `aminos skills` (versions épinglées, empreintes).

## Cachet, signature, certificat

- **Cachet et signature** : déposez les images de *votre* cachet et de *votre* signature (profil → Traducteur, ou `set stamp_image` / `set signature_image`).
- **Signature numérique réelle** : `set cert`, `set key`, `set ca` (PEM) ou `set p12 chemin.p12` avec le mot de passe dans la variable `AMINOS_P12_PASSWORD`. La clé reste sur le serveur ; **aucune clé n'est envoyée par l'interface web**. La valeur légale dépend de votre certificat (qualifié eIDAS ou non), pas de cet outil.
- **Sans certificat** : tout est marqué **ESSAI : cachet et signature non officiels** (page, pied de page, cachet), avec une autorité de test. Un dossier d'essai ne peut pas recevoir d'apostille.

## Apostille : ce que l'outil fait et ne fait pas

Fait : prépare le dossier, vérifie qu'il est complet, garde les empreintes, enregistre l'apostille reçue. Ne fait pas : émettre ou simuler une apostille, la vérifier (seule l'autorité émettrice le peut), décider du circuit pour votre pays (la liste de contrôle renvoie à la table d'état et aux autorités compétentes de la HCCH). Confirmez toujours auprès de l'autorité de destination les exigences de traduction assermentée et de légalisation de la signature du traducteur.

## Back-office (`/erp/`)

Clients, dossiers (statuts, échéances, lien vers le travail du superagent), devis, factures numérotés sans trou par année, TVA, paiements, tableau de bord (retards, factures échues, encaissements). Page HTML/Bootstrap servie par l'application, API JSON, SQL (SQLite, un fichier par cabinet). Impression PDF depuis le navigateur. Sécurité : mêmes comptes que l'application (scrypt, verrouillage), session signée `HttpOnly`/`SameSite=Strict`, jeton CSRF, politique CSP stricte, Bootstrap hébergé localement (aucune ressource tierce), journal d'audit.

PHP et Java ne sont pas utilisés : ils ajouteraient deux environnements d'exécution à installer et à sécuriser sans rien apporter de plus que Python.

## Installer

| Cible | Commande |
|---|---|
| **Ubuntu 22.04 / 24.04** (sans Docker) | `curl -fsSL -o install.sh https://raw.githubusercontent.com/aminecopilote/Aminos/<ref>/deploy/ubuntu/install.sh` puis `sudo bash install.sh --domain votre.domaine --pdf` |
| **Ubuntu avec Docker** | `deploy/install.sh --domain votre.domaine` (le service `erp` est inclus) |
| **Windows Server / Windows 10-11** | `.\bootstrap.ps1 -Ref <ref> -Saas -Domain votre.domaine` (voir `deploy/windows/LISEZ-MOI.md`) ; le back-office est le service `Aminos-ERP` |

Ubuntu natif : services systemd `aminos` (8501) et `aminos-erp` (8502) liés à 127.0.0.1, Caddy en frontal (HTTPS automatique avec un nom de domaine), pare-feu `ufw`, utilisateur système dédié, mot de passe administrateur dans `/etc/aminos/` (jamais dans le dépôt). `--update` garde comptes, données et secrets ; `--uninstall` garde les données.

`--pdf` installe LibreOffice Writer : sans lui, la traduction certifiée ne comprend que la page de certification (les pages traduites restent dans le `.docx` signé à part).

## Confidentialité

Les modèles distants sont désactivés par défaut (deux verrous). Avec `ollama` sur le serveur, les documents ne le quittent pas. Colab, Render et tout fournisseur distant envoient le texte à un tiers : pas de pièces confidentielles.

## Non testé / limites

Voir `deploy/DEPLOY.md`. En plus : `install.sh` Ubuntu n'est exécuté que par la CI (runner GitHub, sans Caddy ni `ufw`) ; Caddy et `ufw` sont les mêmes que dans l'installateur Docker déjà éprouvé mais pas vérifiés sur un VPS réel ; aucune traduction par un vrai modèle ; aucune signature avec un certificat qualifié réel ; l'arabe dans le PDF dépend d'une police arabe présente (DejaVu sous Ubuntu, Arial sous Windows). Une seule instance (SQLite). RGPD et secret professionnel : à faire valider.
