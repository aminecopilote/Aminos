import { Link } from 'react-router-dom'
import Icone from '../components/Icone.jsx'
import Logo from '../components/Logo.jsx'
import { coordonnees, services } from './contenu.js'

export default function PiedDePage() {
  return (
    <footer className="bg-marine-950 text-marine-200">
      <div className="wrap py-16 lg:py-20">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1.2fr]">
          <div>
            <Logo sombre />
            <p className="mt-6 max-w-sm text-sm leading-relaxed text-marine-300">Cabinet de conseil basé à Casablanca. Nous accompagnons les entrepreneurs, TPE et PME marocaines sur l’ensemble de leurs obligations juridiques, comptables, fiscales et sociales.</p>
          </div>
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-white">Expertises</h3>
            <ul className="mt-5 space-y-3 text-sm">
              {services.map((s) => <li key={s.titre}><a href="#services" className="hover:text-white">{s.titre}</a></li>)}
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-white">Cabinet</h3>
            <ul className="mt-5 space-y-3 text-sm">
              <li><a href="#valeur-ajoutee" className="hover:text-white">Notre valeur ajoutée</a></li>
              <li><a href="#methode" className="hover:text-white">Notre méthode</a></li>
              <li><a href="#faq" className="hover:text-white">Questions fréquentes</a></li>
              <li><a href="#contact" className="hover:text-white">Contact</a></li>
              <li><Link to="/espace-client" className="hover:text-white">Espace client EKA SYSTÈME</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-white">Contact</h3>
            <ul className="mt-5 space-y-4 text-sm">
              <li className="flex gap-3"><Icone nom="pin" className="mt-0.5 h-4 w-4 shrink-0 text-or-400" /><span>{coordonnees.adresse}<br />{coordonnees.quartier}</span></li>
              <li className="flex gap-3"><Icone nom="phone" className="mt-0.5 h-4 w-4 shrink-0 text-or-400" /><span className="select-all">{coordonnees.telephone}</span></li>
              <li className="flex gap-3"><Icone nom="mail" className="mt-0.5 h-4 w-4 shrink-0 text-or-400" /><span className="select-all">{coordonnees.email}</span></li>
              <li className="flex gap-3"><Icone nom="clock" className="mt-0.5 h-4 w-4 shrink-0 text-or-400" /><span>{coordonnees.horaires}</span></li>
            </ul>
          </div>
        </div>
        <div className="mt-14 flex flex-col gap-4 border-t border-white/10 pt-8 text-xs text-marine-400 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 EKA CONSEIL — Tous droits réservés. Plateforme EKA SYSTÈME.</p>
          <ul className="flex flex-wrap gap-x-6 gap-y-2">
            <li><a href="#mentions" className="hover:text-white">Mentions légales</a></li>
            <li><a href="#confidentialite" className="hover:text-white">Politique de confidentialité</a></li>
            <li><a href="#cgv" className="hover:text-white">Conditions générales</a></li>
          </ul>
        </div>
      </div>
    </footer>
  )
}
