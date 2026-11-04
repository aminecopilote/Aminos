# Mémoires et terminologies publiques (ONU, UE) — sources et état

Les importeurs (`aminos corpus tmx|moses|tbx`) sont écrits et testés sur de petits jeux d'essai.
**Aucun corpus réel n'a pu être téléchargé depuis la session cloud** : la politique réseau n'autorise que
PyPI, npm et GitHub. Les hôtes suivants ont été essayés et refusés (HTTP 403 par le proxy) :
`opus.nlpl.eu`, `object.pouta.csc.fi`, `conferences.unite.un.org`, `iate.europa.eu`, `data.europa.eu`,
`op.europa.eu`, `wt-public.emm4u.eu`, `unterm.un.org`, `huggingface.co`, `zenodo.org`, `archive.org`,
ainsi que les serveurs d'horodatage (`timestamp.digicert.com`, `freetsa.org`, `opentimestamps.org`).
Pour les utiliser en cloud : Paramètres de l'environnement → Accès réseau → ajouter ces domaines.
Sinon, téléchargez les fichiers sur votre poste et lancez les importeurs en local.

## Ce que chaque source couvre (à vérifier avant usage, y compris la licence)

| Source | Format | ar | fr | en | nl | Notes |
|---|---|:-:|:-:|:-:|:-:|---|
| UN Parallel Corpus (UNPC), MultiUN | TMX / Moses (OPUS) | oui | oui | oui | non | six langues de l'ONU, textes officiels |
| Europarl | TMX / Moses (OPUS) | non | oui | oui | oui | débats du Parlement européen, registre parlementaire |
| DGT-TM, JRC-Acquis | TMX | non | oui | oui | oui | législation de l'UE, registre juridique, le plus proche d'un acte |
| IATE | TBX | non | oui | oui | oui | base terminologique de l'UE |
| UNTERM | export du portail | oui | oui | oui | non | terminologie de l'ONU |

**Aucune ressource publique ne couvre à la fois l'arabe et le néerlandais.** Les paires `ar↔fr`, `ar↔en`
viennent de l'ONU ; `nl↔fr`, `nl↔en` de l'UE. Pour `ar↔nl`, il faut passer par le français ou l'anglais
(pivot) : **non implémenté** — la mémoire ne stocke que des paires directes.

## Commandes

```bash
# TMX (DGT-TM, UNPC, Europarl) : toutes les paires parmi les langues gardées, dans les deux sens
aminos corpus tmx DGT-TM.tmx.gz --db tm.sqlite --langs fr,en,nl
# Deux fichiers alignés ligne à ligne (OPUS « Moses »)
aminos corpus moses UNPC.ar-fr.ar UNPC.ar-fr.fr --langs ar,fr --db tm.sqlite
# Base terminologique TBX -> glossaire utilisable par `translate -g`
aminos corpus tbx IATE.tbx -s fr -t nl -o glossary_fr_nl.json
aminos tm stats tm.sqlite
```

Un corpus ONU complet se compte en dizaines de millions de segments : la recherche approchée passe par un
index FTS5 (quelques centaines de candidats évalués) et non plus par un balayage complet. Non mesuré à cette
échelle faute de corpus réel ; prévoir de la place disque (plusieurs Go) et d'importer par paire de langues.
