// Accès tolérant à sessionStorage : navigation privée ou stockage bloqué ne cassent pas l'app.
export function lire(cle) {
  try {
    return window.sessionStorage.getItem(cle)
  } catch {
    return null
  }
}

export function ecrire(cle, valeur) {
  try {
    if (valeur == null) window.sessionStorage.removeItem(cle)
    else window.sessionStorage.setItem(cle, valeur)
  } catch {
    /* stockage indisponible : la session reste en mémoire le temps de l'onglet */
  }
}
