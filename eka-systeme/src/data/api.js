// Couche d'accès aux données de l'espace client.
// Aujourd'hui tout est simulé à partir de mock.js ; un backend réel remplacera
// le corps de ces fonctions en gardant les mêmes signatures asynchrones.
import * as mock from './mock.js'

const CLE_SESSION = 'eka-session'
const copie = (v) => structuredClone(v)

function lireStockage() {
  try {
    return window.sessionStorage.getItem(CLE_SESSION)
  } catch {
    return null
  }
}

function ecrireStockage(valeur) {
  try {
    if (valeur == null) window.sessionStorage.removeItem(CLE_SESSION)
    else window.sessionStorage.setItem(CLE_SESSION, valeur)
  } catch {
    /* stockage indisponible : la session reste en mémoire le temps de l'onglet */
  }
}

// ── Authentification (simulée)
export async function login(email, motDePasse) {
  const ok =
    email.trim().toLowerCase() === mock.COMPTE_DEMO.email && motDePasse === mock.COMPTE_DEMO.motDePasse
  if (!ok) throw new Error('Identifiants incorrects.')
  ecrireStockage('demo')
  return getSession()
}

export async function logout() {
  ecrireStockage(null)
}

export async function getSession() {
  if (lireStockage() !== 'demo') return null
  return copie(mock.client)
}

// ── Données métier (simulées)
export async function getDossiers() {
  return copie(mock.dossiers)
}

export async function getDossier(id) {
  return copie(mock.dossiers.find((d) => d.id === id) ?? null)
}

export async function getEcheances() {
  return copie(mock.echeances)
}

export async function getPaie() {
  return copie(mock.paie)
}

export async function getDocuments() {
  return copie(mock.documents)
}

export async function getActivite() {
  return copie(mock.activite)
}
