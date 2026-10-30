import { useEffect, useState } from 'react'
import Icone from '../components/Icone.jsx'
import Contact from './Contact.jsx'
import EnTete from './EnTete.jsx'
import PiedDePage from './PiedDePage.jsx'
import { Faq, Hero, Indicateurs, Methode, Relance, Services, ValeurAjoutee } from './Sections.jsx'
import { coordonnees } from './contenu.js'

// Bouton WhatsApp flottant : apparaît après le premier écran.
function BoutonWhatsApp() {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const maj = () => setVisible(window.scrollY > 420)
    maj()
    window.addEventListener('scroll', maj, { passive: true })
    return () => window.removeEventListener('scroll', maj)
  }, [])
  return (
    <a href={coordonnees.whatsapp} target="_blank" rel="noopener noreferrer" aria-label="Nous contacter sur WhatsApp" tabIndex={visible ? 0 : -1}
      className={`fixed z-50 flex items-center gap-3 rounded-full bg-[#25D366] py-3 pl-3 pr-4 shadow-float transition-all duration-300 hover:bg-[#1FBF5B] ${visible ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'}`}
      style={{ bottom: 'calc(1.5rem + env(safe-area-inset-bottom, 0px))', right: 'calc(1.5rem + env(safe-area-inset-right, 0px))' }}>
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-white"><Icone nom="whatsapp" trait={1.5} /></span>
      <span className="hidden text-sm font-semibold text-white sm:block">Discuter sur WhatsApp</span>
    </a>
  )
}

export default function Vitrine() {
  useEffect(() => {
    document.title = 'EKA CONSEIL — Casablanca'
  }, [])
  return (
    <>
      <EnTete />
      <main>
        <Hero />
        <Indicateurs />
        <Services />
        <ValeurAjoutee />
        <Methode />
        <Faq />
        <Relance telephone={coordonnees.telephone} />
        <Contact />
      </main>
      <PiedDePage />
      <BoutonWhatsApp />
    </>
  )
}
