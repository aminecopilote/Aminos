// Couche d'accès aux données de l'espace client.
// Les écrans n'importent que ce module ; il délègue à l'adaptateur choisi par
// VITE_EKA_API : « mock » (défaut, données de mock.js en mémoire) ou « http »
// (API REST à l'adresse VITE_EKA_API_URL, voir server/ et le README).
// Brancher un autre backend (Supabase, API du cabinet…) = écrire un adaptateur
// qui respecte l'interface Adaptateur de types.js et l'ajouter ci-dessous.
import { creerAdaptateurHttp } from './adaptateurs/http.js'
import { creerAdaptateurMock } from './adaptateurs/mock.js'

export function creerAdaptateur(env = import.meta.env) {
  const mode = (env.VITE_EKA_API || 'mock').toLowerCase()
  if (mode === 'http') return creerAdaptateurHttp({ baseUrl: env.VITE_EKA_API_URL || '/api' })
  if (mode === 'mock') return creerAdaptateurMock()
  throw new Error(`VITE_EKA_API inconnu : « ${mode} » (attendu : mock ou http).`)
}

const adaptateur = creerAdaptateur()

export const login = (email, motDePasse) => adaptateur.login(email, motDePasse)
export const logout = () => adaptateur.logout()
export const getSession = () => adaptateur.getSession()
export const getDossiers = () => adaptateur.getDossiers()
export const getDossier = (id) => adaptateur.getDossier(id)
export const getEcheances = () => adaptateur.getEcheances()
export const getPaie = () => adaptateur.getPaie()
export const getDocuments = () => adaptateur.getDocuments()
export const getActivite = () => adaptateur.getActivite()
