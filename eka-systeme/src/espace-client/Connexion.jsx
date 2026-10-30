import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Monogramme } from '../components/Logo.jsx'
import { COMPTE_DEMO } from '../data/mock.js'
import { useSession } from './session.jsx'

const CHAMP = 'mt-2 w-full rounded-lg border border-ardoise-200 bg-white px-4 py-3 text-marine-900 shadow-sm focus:border-marine-400 focus:outline-none focus:ring-2 focus:ring-marine-200'

// Connexion simulée : un seul compte de démonstration, rien n'est envoyé à un serveur.
export default function Connexion() {
  const { client, chargement, connecter } = useSession()
  const naviguer = useNavigate()
  const { state } = useLocation()
  const [email, setEmail] = useState(COMPTE_DEMO.email)
  const [motDePasse, setMotDePasse] = useState(COMPTE_DEMO.motDePasse)
  const [erreur, setErreur] = useState('')
  const [envoi, setEnvoi] = useState(false)

  useEffect(() => {
    document.title = 'Connexion — EKA SYSTÈME'
  }, [])

  if (!chargement && client) return <Navigate to={state?.depuis || '/espace-client'} replace />

  const envoyer = async (e) => {
    e.preventDefault()
    setEnvoi(true)
    try {
      await connecter(email, motDePasse)
      naviguer(state?.depuis || '/espace-client', { replace: true })
    } catch (err) {
      setErreur(err.message)
      setEnvoi(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-marine-950">
      <div className="gouttiere mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-16">
        <Link to="/" className="flex items-center gap-3">
          <Monogramme sombre />
          <span className="flex flex-col leading-none">
            <span className="text-sm font-extrabold tracking-tight text-white">EKA SYSTÈME</span>
            <span className="mt-1 text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-marine-300">Espace client</span>
          </span>
        </Link>
        <form onSubmit={envoyer} aria-label="Connexion à l’espace client" className="mt-8 rounded-2xl bg-white p-7 shadow-float">
          <h1 className="text-xl font-semibold">Connexion à votre espace</h1>
          <p className="mt-2 text-sm text-ardoise-500">Démonstration : les identifiants du compte d’essai sont préremplis.</p>
          <label htmlFor="cx-email" className="mt-6 block text-sm font-semibold text-marine-800">Adresse e-mail</label>
          <input id="cx-email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} className={CHAMP} />
          <label htmlFor="cx-mdp" className="mt-5 block text-sm font-semibold text-marine-800">Mot de passe</label>
          <input id="cx-mdp" type="password" autoComplete="current-password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} className={CHAMP} />
          {erreur && <p role="alert" className="mt-5 rounded-lg bg-red-50 p-3 text-sm font-medium text-red-700">{erreur}</p>}
          <button type="submit" disabled={envoi} className="mt-7 w-full rounded-lg bg-marine-800 px-6 py-3 text-base font-semibold text-white transition hover:bg-marine-700 disabled:opacity-60">Se connecter</button>
        </form>
        <Link to="/" className="mt-6 text-center text-sm font-medium text-marine-300 hover:text-white">← Retour au site EKA CONSEIL</Link>
      </div>
    </div>
  )
}
