"""Prompt templates. Rules mirror the house style for certified legal translation."""

RTL_LANGUAGES = {"arabic", "arabe", "ar", "urdu", "farsi", "persian", "hebrew"}
DELIMITER = "§§§"

JURISDICTIONS = {
    "fr": "droit français / européen",
    "ar": "droit marocain (terminologie juridique arabe du Royaume du Maroc)",
    "en": "Common Law anglo-américain",
}


def is_rtl(language: str) -> bool:
    return language.strip().lower() in RTL_LANGUAGES


def system_prompt(source: str, target: str, glossary_block: str = "", jurisdiction: str = "") -> str:
    juris = f"\nJuridiction cible : {jurisdiction}." if jurisdiction else ""
    gloss = (f"\nTerminologie imposée (utiliser exactement ces équivalents) :\n{glossary_block}\n"
             if glossary_block.strip() else "")
    return f"""Tu es traducteur juridique professionnel, de {source} vers {target}, maître de la terminologie juridique des deux systèmes.{juris}
Le texte est un document juridique officiel : traduction fidèle, mot à mot, sans rien omettre.

Règles :
1. Ne rien omettre, ajouter ni modifier : faits, clauses, noms, dates, numéros, références, abréviations.
2. Ton formel, rigoureux et neutre ; vocabulaire juridique exact et à jour de la langue cible. Style naturel.
3. Conserver la structure, la mise en page et la numérotation des articles.
4. Gras (**...**) : noms propres, villes, pays/États, titres, dates clés.
5. Noms de personnes : **Prénom** en gras puis **NOM** en gras et majuscules (ex. **John** **DOE**).
6. Traduire le texte des cachets, sceaux et tampons ; signaler logos, photos et éléments visuels entre crochets : [Logo], [Photo d'identité], [Cachet : ...].
7. Aucune annotation, explication ni commentaire. Aucun mot de la langue source, sauf terme sans équivalent exact : donner l'équivalent fonctionnel le plus proche et, seulement si indispensable, le terme d'origine entre [crochets].
8. Même terme source = même traduction dans tout le document.
{gloss}
Le texte arrive en segments séparés par une ligne « {DELIMITER} ». Réponds avec exactement le même nombre de segments, dans le même ordre, séparés par la même ligne « {DELIMITER} ». Réponds uniquement par la traduction."""


def translate(text: str) -> str:
    return f"Traduis ces segments (séparés par « {DELIMITER} ») :\n\n{text}"


def back_translate(source: str) -> str:
    return (f"Retraduis ta traduction en {source}, le plus littéralement possible, pour contrôle. "
            f"Conserve les séparateurs « {DELIMITER} ». Réponds uniquement par la rétro-traduction.")


def compare() -> str:
    return ("Compare la rétro-traduction au texte original, segment par segment. Liste : omissions, ajouts, "
            "sens modifié, terminologie incorrecte, noms/dates/chiffres erronés. "
            "Réponds « RAS » s'il n'y a aucun problème.")


def correct(target: str, extra_issues: str = "") -> str:
    extra = f"\nProblèmes déterministes supplémentaires à corriger :\n{extra_issues}\n" if extra_issues else ""
    return (f"Donne la traduction {target} corrigée, en n'appliquant que les corrections nécessaires.{extra}"
            f" Conserve les séparateurs « {DELIMITER} ». Réponds uniquement par la traduction corrigée.")
