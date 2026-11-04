## Orchestrateur

- Skill : `skills/orchestrateur-central/SKILL.md` ; commande `aminos orchestrate`. Journal : `C:\orchestrator\logs\orch-<date>.jsonl`.
- Seuils : CPU > 90 %, mémoire libre < 500 Mo, redémarrages Docker > 3, événement Erreur+ en 5 min.
- Les actions sont proposées ; exécutées seulement avec `--execute` et si elles sont dans la liste blanche (`Restart-Service` de quelques services, `docker restart`).
- Le chef d'agence est décrit dans `agency/AGENTS.md`.
