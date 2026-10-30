// Adaptateur HTTP : parle à une API REST (le serveur de server/ ou un backend réel
// qui respecte le même contrat, décrit dans le README). Authentification par jeton
// Bearer obtenu à la connexion et gardé dans sessionStorage.
import { ecrire, lire } from '../stockage.js'

const CLE_JETON = 'eka-jeton'

export class ErreurApi extends Error {
  constructor(message, statut) {
    super(message)
    this.name = 'ErreurApi'
    this.statut = statut
  }
}

/**
 * @param {{baseUrl: string, fetch?: typeof fetch}} options
 * @returns {import('../types.js').Adaptateur}
 */
export function creerAdaptateurHttp({ baseUrl, fetch: fetchImpl = (...a) => globalThis.fetch(...a) }) {
  const racine = baseUrl.replace(/\/+$/, '')

  async function requete(chemin, { methode = 'GET', corps } = {}) {
    const jeton = lire(CLE_JETON)
    const entetes = { Accept: 'application/json' }
    if (corps !== undefined) entetes['Content-Type'] = 'application/json'
    if (jeton) entetes.Authorization = `Bearer ${jeton}`
    let reponse
    try {
      reponse = await fetchImpl(racine + chemin, {
        method: methode,
        headers: entetes,
        body: corps === undefined ? undefined : JSON.stringify(corps),
      })
    } catch {
      throw new ErreurApi('Serveur injoignable.', 0)
    }
    if (reponse.status === 401) ecrire(CLE_JETON, null)
    if (reponse.status === 204) return null
    const donnees = await reponse.json().catch(() => null)
    if (!reponse.ok) throw new ErreurApi(donnees?.erreur || `Erreur ${reponse.status}`, reponse.status)
    return donnees
  }

  return {
    async login(email, motDePasse) {
      const { jeton, client } = await requete('/auth/connexion', { methode: 'POST', corps: { email, motDePasse } })
      ecrire(CLE_JETON, jeton)
      return client
    },
    async logout() {
      if (lire(CLE_JETON)) await requete('/auth/deconnexion', { methode: 'POST' }).catch(() => {})
      ecrire(CLE_JETON, null)
    },
    async getSession() {
      if (!lire(CLE_JETON)) return null
      try {
        return await requete('/auth/session')
      } catch (e) {
        if (e.statut === 401) return null
        throw e
      }
    },
    getDossiers: () => requete('/dossiers'),
    async getDossier(id) {
      try {
        return await requete(`/dossiers/${encodeURIComponent(id)}`)
      } catch (e) {
        if (e.statut === 404) return null
        throw e
      }
    },
    getEcheances: () => requete('/echeances'),
    getPaie: () => requete('/paie'),
    getDocuments: () => requete('/documents'),
    getActivite: () => requete('/activite'),
  }
}
