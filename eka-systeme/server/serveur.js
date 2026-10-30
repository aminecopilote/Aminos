// Serveur d'API de démonstration pour l'espace client (Node ≥ 18, sans dépendance).
// Il implémente le contrat REST consommé par src/data/adaptateurs/http.js et sert
// les données de src/data/mock.js. Sessions en mémoire : un redémarrage déconnecte tout.
// À remplacer par le vrai backend du cabinet, qui n'aura qu'à respecter les mêmes routes.
import { randomBytes, timingSafeEqual } from 'node:crypto'
import { createServer } from 'node:http'
import { pathToFileURL } from 'node:url'
import * as mock from '../src/data/mock.js'

// Un compte par client ; un vrai backend lira ses utilisateurs et données en base.
const COMPTES = [{ email: mock.COMPTE_DEMO.email, motDePasse: mock.COMPTE_DEMO.motDePasse, clientId: 'atlas-negoce' }]
const DONNEES = {
  'atlas-negoce': {
    client: mock.client,
    dossiers: mock.dossiers,
    echeances: mock.echeances,
    paie: mock.paie,
    documents: mock.documents,
    activite: mock.activite,
  },
}

const egal = (a, b) => {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b))
  return x.length === y.length && timingSafeEqual(x, y)
}

/**
 * @param {{prefixe?: string, origineCors?: string, dureeSessionMin?: number}} [options]
 */
export function creerServeur({ prefixe = '/api', origineCors = '', dureeSessionMin = 120 } = {}) {
  const sessions = new Map() // jeton → { clientId, expire }

  function envoyer(res, statut, corps) {
    res.writeHead(statut, corps === undefined ? {} : { 'Content-Type': 'application/json; charset=utf-8' })
    res.end(corps === undefined ? undefined : JSON.stringify(corps))
  }

  async function lireCorps(req) {
    let brut = ''
    for await (const morceau of req) {
      brut += morceau
      if (brut.length > 10_000) throw new Error('trop long')
    }
    return brut ? JSON.parse(brut) : {}
  }

  function sessionDe(req) {
    const [type, jeton] = (req.headers.authorization || '').split(' ')
    if (type !== 'Bearer' || !jeton) return null
    const session = sessions.get(jeton)
    if (!session) return null
    if (session.expire < Date.now()) {
      sessions.delete(jeton)
      return null
    }
    return { jeton, ...session }
  }

  return createServer(async (req, res) => {
    if (origineCors) {
      res.setHeader('Access-Control-Allow-Origin', origineCors)
      res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type')
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
      res.setHeader('Vary', 'Origin')
    }
    if (req.method === 'OPTIONS') return envoyer(res, 204)

    const url = new URL(req.url, 'http://localhost')
    if (!url.pathname.startsWith(prefixe + '/')) return envoyer(res, 404, { erreur: 'Route inconnue.' })
    const chemin = url.pathname.slice(prefixe.length)

    try {
      if (req.method === 'POST' && chemin === '/auth/connexion') {
        const { email = '', motDePasse = '' } = await lireCorps(req)
        const compte = COMPTES.find((c) => egal(c.email, String(email).trim().toLowerCase()))
        if (!compte || !egal(compte.motDePasse, motDePasse)) return envoyer(res, 401, { erreur: 'Identifiants incorrects.' })
        const jeton = randomBytes(32).toString('base64url')
        sessions.set(jeton, { clientId: compte.clientId, expire: Date.now() + dureeSessionMin * 60_000 })
        return envoyer(res, 200, { jeton, client: DONNEES[compte.clientId].client })
      }

      const session = sessionDe(req)
      if (!session) return envoyer(res, 401, { erreur: 'Session absente ou expirée.' })
      const donnees = DONNEES[session.clientId]

      if (req.method === 'POST' && chemin === '/auth/deconnexion') {
        sessions.delete(session.jeton)
        return envoyer(res, 204)
      }
      if (req.method !== 'GET') return envoyer(res, 405, { erreur: 'Méthode non autorisée.' })
      if (chemin === '/auth/session') return envoyer(res, 200, donnees.client)

      const dossier = chemin.match(/^\/dossiers\/([^/]+)$/)
      if (dossier) {
        const d = donnees.dossiers.find((x) => x.id === decodeURIComponent(dossier[1]))
        return d ? envoyer(res, 200, d) : envoyer(res, 404, { erreur: 'Dossier introuvable.' })
      }
      const ressource = { '/dossiers': 'dossiers', '/echeances': 'echeances', '/paie': 'paie', '/documents': 'documents', '/activite': 'activite' }[chemin]
      if (ressource) return envoyer(res, 200, donnees[ressource])
      return envoyer(res, 404, { erreur: 'Route inconnue.' })
    } catch {
      return envoyer(res, 400, { erreur: 'Requête invalide.' })
    }
  })
}

// Lancement direct : `npm run api`.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.EKA_API_PORT || 8787)
  const hote = process.env.EKA_API_HOST || '127.0.0.1'
  creerServeur({
    origineCors: process.env.EKA_API_CORS_ORIGIN || '',
    dureeSessionMin: Number(process.env.EKA_API_SESSION_MIN || 120),
  }).listen(port, hote, () => console.log(`API EKA de démonstration sur http://${hote}:${port}/api`))
}
