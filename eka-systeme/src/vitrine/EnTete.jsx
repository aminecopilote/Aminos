import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icone from '../components/Icone.jsx'
import Logo from '../components/Logo.jsx'
import { ancres, coordonnees } from './contenu.js'

export default function EnTete() {
  const [ouvert, setOuvert] = useState(false)
  const fermer = () => setOuvert(false)

  return (
    <header className="sticky top-0 z-50 border-b border-ardoise-100 bg-white/95 backdrop-blur">
      <div className="hidden bg-marine-900 lg:block">
        <div className="wrap flex h-10 items-center justify-between text-xs text-marine-200">
          <p className="flex items-center gap-2"><Icone nom="pin" className="h-3.5 w-3.5 text-or-400" /> {coordonnees.adresse}, Maârif — Casablanca</p>
          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2"><Icone nom="phone" className="h-3.5 w-3.5 text-or-400" /> {coordonnees.telephone}</span>
            <span className="flex items-center gap-2"><Icone nom="mail" className="h-3.5 w-3.5 text-or-400" /> {coordonnees.email}</span>
          </div>
        </div>
      </div>

      <div className="wrap flex h-20 items-center justify-between gap-6">
        <Logo />

        <nav className="hidden items-center gap-1 xl:flex" aria-label="Navigation principale">
          {ancres.slice(0, 4).map((a) => (
            <a key={a.id} href={`#${a.id}`} className="whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium text-ardoise-600 transition hover:bg-marine-50 hover:text-marine-800">{a.libelle}</a>
          ))}
        </nav>

        <div className="hidden shrink-0 items-center gap-3 xl:flex">
          <Link to="/espace-client" className="inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-3 text-sm font-semibold text-marine-800 ring-1 ring-inset ring-ardoise-200 transition hover:bg-marine-50">Espace client</Link>
          <a href="#contact" className="inline-flex items-center gap-2 whitespace-nowrap rounded-lg bg-marine-800 px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-marine-700">
            <span className="2xl:hidden">Consultation</span><span className="hidden 2xl:inline">Demander une consultation</span> <Icone nom="arrow" className="h-4 w-4" trait={2} />
          </a>
        </div>

        <button type="button" onClick={() => setOuvert(!ouvert)} aria-expanded={ouvert} aria-controls="menu-mobile" aria-label={ouvert ? 'Fermer le menu' : 'Ouvrir le menu'}
          className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-marine-800 ring-1 ring-inset ring-ardoise-200 xl:hidden">
          <Icone nom={ouvert ? 'close' : 'menu'} className="h-5 w-5" />
        </button>
      </div>

      <div id="menu-mobile" hidden={!ouvert} className="border-t border-ardoise-100 bg-white xl:hidden">
        <div className="wrap flex flex-col gap-1 py-5">
          {ancres.slice(0, 4).map((a) => (
            <a key={a.id} href={`#${a.id}`} onClick={fermer} className="rounded-lg px-3 py-3 text-base font-medium text-marine-800 hover:bg-marine-50">{a.libelle}</a>
          ))}
          <Link to="/espace-client" onClick={fermer} className="rounded-lg px-3 py-3 text-base font-medium text-marine-800 hover:bg-marine-50">Espace client</Link>
          <a href="#contact" onClick={fermer} className="mt-3 inline-flex items-center justify-center gap-2 rounded-lg bg-marine-800 px-7 py-3.5 text-base font-semibold text-white">Demander une consultation</a>
        </div>
      </div>
    </header>
  )
}
