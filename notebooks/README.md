# Carnets Google Colab (GPU gratuit)

| Carnet | Rôle |
|---|---|
| [`OpenClaw-GPU-Test.ipynb`](OpenClaw-GPU-Test.ipynb) | **À faire en premier** : vérifie que votre compte obtient un GPU gratuit (aucun fichier envoyé, données aléatoires) |
| [`aminos_colab_gpu.ipynb`](aminos_colab_gpu.ipynb) | Traduit un document avec un modèle local sur le GPU Colab (le document est traité chez Google) |

Ouvrir dans Colab : *Fichier > Ouvrir le notebook > GitHub*, puis `aminecopilote/Aminos` (branche `main` après fusion de la PR, sinon la branche de la PR).

## Le test du GPU, pas à pas
1. **Créer le carnet** : ouvrez Google Colab, connectez-vous, ouvrez `OpenClaw-GPU-Test.ipynb` (aucune installation sur votre PC).
2. **Activer le GPU** : *Exécution > Modifier le type d'exécution*, accélérateur **GPU** (ou **T4 GPU**), enregistrer, *Se connecter*. Le GPU gratuit dépend des disponibilités et de vos quotas ; T4, P100 ou 15 Go ne sont pas garantis. Si Colab ne propose qu'une offre payante, ne souscrivez pas : réessayez plus tard.
3. **Vérifier le GPU attribué** : cellules 1 (`nvidia-smi`) et 2 (PyTorch). Notez le **nom du GPU** et sa mémoire.
4. **Tester un calcul** : cellule 3 (multiplication de matrices aléatoires sur le GPU).
5. **Libérer** : *Exécution > Se déconnecter et supprimer l'environnement d'exécution*.

## Utilisation avec OpenClaw
Commencer par un traitement ponctuel :

| Étape | Où |
|---|---|
| Préparer le script et les paramètres | OpenClaw sur votre PC |
| Ouvrir le carnet et lancer la session | Vous, dans Colab |
| Exécuter le calcul lourd | GPU Colab |
| Télécharger et exploiter les résultats | PC / OpenClaw |

Gardez la mémoire quotidienne d'OpenClaw sur Ollama local : Colab convient aux traitements par lots, pas à une mémoire qui doit rester disponible en permanence.

## Limites
- **Colab est le cloud de Google** : tout ce que vous y déposez y est traité. Pas de pièces confidentielles.
- Disponibilité et durée de session variables, sans garantie.
- N'utilisez pas Colab comme serveur joignable de l'extérieur (tunnels) : ses conditions d'usage l'interdisent pour les machines gratuites ; c'est pourquoi aucun carnet ne fait cela.
