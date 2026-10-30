// Adaptateur en mémoire : sert les données de mock.js sans réseau.
// C'est l'adaptateur par défaut (démo, tests, développement sans serveur).
import * as mock from '../mock.js'
import { ecrire, lire } from '../stockage.js'

const CLE_SESSION = 'eka-session'
const copie = (v) => structuredClone(v)

/** @returns {import('../types.js').Adaptateur} */
export function creerAdaptateurMock() {
  const getSession = async () => (lire(CLE_SESSION) === 'demo' ? copie(mock.client) : null)
  return {
    async login(email, motDePasse) {
      const ok =
        email.trim().toLowerCase() === mock.COMPTE_DEMO.email && motDePasse === mock.COMPTE_DEMO.motDePasse
      if (!ok) throw new Error('Identifiants incorrects.')
      ecrire(CLE_SESSION, 'demo')
      return getSession()
    },
    async logout() {
      ecrire(CLE_SESSION, null)
    },
    getSession,
    getDossiers: async () => copie(mock.dossiers),
    getDossier: async (id) => copie(mock.dossiers.find((d) => d.id === id) ?? null),
    getEcheances: async () => copie(mock.echeances),
    getPaie: async () => copie(mock.paie),
    getDocuments: async () => copie(mock.documents),
    getActivite: async () => copie(mock.activite),
  }
}
