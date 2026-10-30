import { useEffect } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import Icone from '../components/Icone.jsx'
import { Monogramme } from '../components/Logo.jsx'
import { useSession } from './session.jsx'

export const RUBRIQUES = [
  { chemin: '/espace-client', libelle: 'Tableau de bord', icone: 'cpu', exact: true },
  { chemin: '/espace-client/dossiers', libelle: 'Mes dossiers', icone: 'document' },
  { chemin: '/espace-client/echeancier', libelle: 'Échéancier', icone: 'clock' },
  { chemin: '/espace-client/paie', libelle: 'Paie & RH', icone: 'users' },
  { chemin: '/espace-client/documents', libelle: 'Coffre-fort', icone: 'cloud' },
]

// Mise en page produit : navigation fixe à gauche (≥ 1024 px), repliée en onglets défilants dessous.
export default function Gabarit() {
  const { client, deconnecter } = useSession()
  const naviguer = useNavigate()
  const { pathname } = useLocation()

  useEffect(() => {
    document.title = 'EKA SYSTÈME — Espace client'
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [pathname])

  const sortir = async () => {
    await deconnecter()
    naviguer('/espace-client/connexion', { replace: true })
  }

  return (
    <div className="min-h-screen bg-ardoise-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-marine-950 lg:flex">
        <Link to="/" className="flex h-20 items-center gap-3 px-5" title="Retour au site EKA CONSEIL">
          <Monogramme sombre />
          <span className="flex flex-col leading-none">
            <span className="text-sm font-extrabold tracking-tight text-white">EKA SYSTÈME</span>
            <span className="mt-1 text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-marine-300">Espace client</span>
          </span>
        </Link>
        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Navigation de l’espace client">
          {RUBRIQUES.map((r) => (
            <NavLink key={r.chemin} to={r.chemin} end={r.exact}
              className={({ isActive }) => `flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-white/10 text-white' : 'text-marine-200 hover:bg-white/5 hover:text-white'}`}>
              <Icone nom={r.icone} className="h-[18px] w-[18px] shrink-0" />
              {r.libelle}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 p-5">
          <p className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-marine-400">Votre interlocuteur</p>
          <p className="mt-2 text-sm font-semibold text-white">{client.interlocuteur.nom}</p>
          <p className="mt-0.5 text-xs text-marine-300">{client.interlocuteur.fonction}</p>
          <span className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-or-300"><Icone nom="mail" className="h-3.5 w-3.5" /> {client.interlocuteur.email}</span>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-ardoise-100 bg-white/95 backdrop-blur">
          <div className="gouttiere flex h-16 items-center gap-4">
            <Link to="/" className="lg:hidden" aria-label="Retour au site EKA CONSEIL"><Monogramme /></Link>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-marine-900">{client.raisonSociale}</p>
              <p className="mt-0.5 truncate text-xs text-ardoise-400">{client.identifiants}</p>
            </div>
            <label className="relative ml-auto hidden max-w-xs flex-1 md:block">
              <span className="sr-only">Rechercher un dossier ou un document</span>
              <Icone nom="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ardoise-400" />
              <input type="search" placeholder="Rechercher un dossier, un document…" className="w-full rounded-lg border border-ardoise-200 bg-ardoise-50 py-2 pl-9 pr-3 text-sm text-marine-900 placeholder:text-ardoise-400 focus:border-marine-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-marine-200" />
            </label>
            <button type="button" aria-label={`${client.notificationsNonLues} notifications non lues`} className="relative ml-auto inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-ardoise-500 ring-1 ring-inset ring-ardoise-200 md:ml-0">
              <Icone nom="bell" className="h-5 w-5" />
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-etat-critique text-[0.6rem] font-bold text-white">{client.notificationsNonLues}</span>
            </button>
            <div className="hidden items-center gap-3 border-l border-ardoise-100 pl-4 sm:flex">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-marine-100 text-xs font-bold text-marine-800">{client.utilisateur.initiales}</span>
              <span className="flex flex-col leading-tight"><span className="text-sm font-semibold text-marine-900">{client.utilisateur.prenom} {client.utilisateur.nom}</span><span className="text-xs text-ardoise-400">{client.utilisateur.fonction}</span></span>
            </div>
            <button type="button" onClick={sortir} aria-label="Se déconnecter" title="Se déconnecter" className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-ardoise-500 ring-1 ring-inset ring-ardoise-200 hover:text-marine-800">
              <Icone nom="logout" className="h-5 w-5" />
            </button>
          </div>
          <nav className="gouttiere flex gap-1 overflow-x-auto border-t border-ardoise-100 py-2 lg:hidden" aria-label="Navigation de l’espace client (mobile)">
            {RUBRIQUES.map((r) => (
              <NavLink key={r.chemin} to={r.chemin} end={r.exact}
                className={({ isActive }) => `shrink-0 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-marine-800 text-white' : 'text-ardoise-600'}`}>
                {r.libelle}
              </NavLink>
            ))}
          </nav>
        </header>

        <main className="gouttiere py-8">
          <Outlet />
        </main>

        <footer className="gouttiere border-t border-ardoise-200 py-6">
          <p className="text-xs text-ardoise-400">EKA SYSTÈME — plateforme de suivi du cabinet <Link to="/" className="underline underline-offset-2 hover:text-marine-800">EKA CONSEIL</Link>, Casablanca. Données de démonstration.</p>
        </footer>
      </div>
    </div>
  )
}
