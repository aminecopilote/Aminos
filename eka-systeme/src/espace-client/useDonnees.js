import { useEffect, useState } from 'react'

// Charge une ressource asynchrone de api.js et expose son état.
export default function useDonnees(charger, deps = []) {
  const [etat, setEtat] = useState({ chargement: true, donnees: null, erreur: null })
  useEffect(() => {
    let actif = true
    setEtat((e) => ({ ...e, chargement: true }))
    charger()
      .then((donnees) => actif && setEtat({ chargement: false, donnees, erreur: null }))
      .catch((erreur) => actif && setEtat({ chargement: false, donnees: null, erreur }))
    return () => {
      actif = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return etat
}
