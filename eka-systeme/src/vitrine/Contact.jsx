import { useState } from 'react'
import Icone from '../components/Icone.jsx'
import { besoins, coordonnees } from './contenu.js'
import { champsManquants } from './validation.js'

const CHAMP = 'mt-2 w-full rounded-lg border border-ardoise-200 bg-white px-4 py-3 text-marine-900 shadow-sm placeholder:text-ardoise-300 focus:border-marine-400 focus:outline-none focus:ring-2 focus:ring-marine-200'
const VIDE = { nom: '', societe: '', email: '', telephone: '', besoin: '', message: '', consentement: false }

function Coordonnee({ icone, titre, children }) {
  return (
    <div className="flex gap-4 py-5">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-marine-50 text-marine-800"><Icone nom={icone} className="h-5 w-5" /></span>
      <div className="min-w-0">
        <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-ardoise-400">{titre}</dt>
        <dd className="mt-1 text-[0.95rem] leading-relaxed text-ardoise-600">{children}</dd>
      </div>
    </div>
  )
}

export default function Contact() {
  const [valeurs, setValeurs] = useState(VIDE)
  const [erreur, setErreur] = useState('')
  const [envoye, setEnvoye] = useState(false)

  const changer = (e) => {
    const { name, type, checked, value } = e.target
    setValeurs((v) => ({ ...v, [name]: type === 'checkbox' ? checked : value }))
  }

  // Envoi simulé : la demande n'est transmise à aucun serveur pour l'instant.
  const envoyer = (e) => {
    e.preventDefault()
    const manques = champsManquants(valeurs)
    if (manques.length) {
      setEnvoye(false)
      setErreur(`Merci d’indiquer ${manques.join(', ')}.`)
      return
    }
    setErreur('')
    setEnvoye(true)
    setValeurs(VIDE)
  }

  return (
    <section id="contact" className="scroll-mt-28 bg-white py-20 lg:py-28">
      <div className="wrap">
        <span className="inline-flex items-center rounded-full bg-marine-50 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-marine-700 ring-1 ring-inset ring-marine-100">Contact &amp; prise de rendez-vous</span>
        <h2 className="mt-5 max-w-3xl text-3xl leading-[1.15] sm:text-4xl lg:text-[2.75rem]">Échangeons sur votre dossier.</h2>
        <p className="mt-5 max-w-3xl text-lg leading-relaxed text-ardoise-500">Premier entretien de diagnostic sans engagement, au cabinet à Casablanca ou en visioconférence.</p>

        <div className="mt-14 grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
          <div>
            <dl className="divide-y divide-ardoise-100 border-y border-ardoise-100">
              <Coordonnee icone="pin" titre="Cabinet">{coordonnees.adresse}<br />{coordonnees.quartier}</Coordonnee>
              <Coordonnee icone="phone" titre="Téléphone"><span className="select-all">{coordonnees.telephone}</span></Coordonnee>
              <Coordonnee icone="mail" titre="E-mail"><span className="select-all">{coordonnees.email}</span></Coordonnee>
              <Coordonnee icone="clock" titre="Horaires">{coordonnees.horaires}</Coordonnee>
            </dl>

            <a href={coordonnees.whatsapp} target="_blank" rel="noopener noreferrer" className="mt-7 flex items-center gap-4 rounded-2xl bg-marine-900 p-6 transition hover:bg-marine-800">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#25D366] text-marine-900"><Icone nom="whatsapp" trait={1.5} /></span>
              <span className="min-w-0"><span className="block font-semibold text-white">Écrire sur WhatsApp</span><span className="mt-1 block text-sm text-marine-200">Réponse immédiate pendant les heures d’ouverture</span></span>
              <Icone nom="arrow" className="ml-auto hidden h-5 w-5 shrink-0 text-or-400 sm:block" />
            </a>

            <div className="mt-6 overflow-hidden rounded-2xl border border-ardoise-100 bg-ardoise-50">
              <div className="flex h-48 flex-col items-center justify-center gap-2 text-center">
                <Icone nom="pin" className="text-marine-400" />
                <p className="px-6 text-sm font-medium text-ardoise-500">{coordonnees.adresse} — Casablanca</p>
                <p className="text-xs text-ardoise-400">Emplacement de la carte (intégration Google Maps)</p>
              </div>
            </div>
          </div>

          <form noValidate onSubmit={envoyer} aria-label="Demande de consultation" className="rounded-2xl border border-ardoise-100 bg-white p-7 shadow-card lg:p-9">
            <h3 className="text-xl font-semibold">Décrivez votre besoin</h3>
            <p className="mt-2 text-sm text-ardoise-500">Réponse sous 24 heures ouvrées. Les champs marqués d’un astérisque sont obligatoires.</p>
            <div className="mt-7 grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="nom" className="block text-sm font-semibold text-marine-800">Nom et prénom <span className="text-or-600">*</span></label>
                <input id="nom" name="nom" type="text" required autoComplete="name" placeholder="Yassine El Amrani" value={valeurs.nom} onChange={changer} className={CHAMP} />
              </div>
              <div>
                <label htmlFor="societe" className="block text-sm font-semibold text-marine-800">Société</label>
                <input id="societe" name="societe" type="text" autoComplete="organization" placeholder="Nom de votre société" value={valeurs.societe} onChange={changer} className={CHAMP} />
                <p className="mt-2 text-sm text-ardoise-400">Laissez vide s’il s’agit d’une création.</p>
              </div>
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-marine-800">Adresse e-mail <span className="text-or-600">*</span></label>
                <input id="email" name="email" type="email" required autoComplete="email" placeholder="vous@societe.ma" value={valeurs.email} onChange={changer} className={CHAMP} />
              </div>
              <div>
                <label htmlFor="telephone" className="block text-sm font-semibold text-marine-800">Téléphone <span className="text-or-600">*</span></label>
                <input id="telephone" name="telephone" type="tel" required inputMode="tel" autoComplete="tel" placeholder="06 12 34 56 78" value={valeurs.telephone} onChange={changer} className={CHAMP} />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="besoin" className="block text-sm font-semibold text-marine-800">Votre besoin <span className="text-or-600">*</span></label>
                <select id="besoin" name="besoin" required value={valeurs.besoin} onChange={changer} className={CHAMP}>
                  <option value="">Sélectionnez un domaine…</option>
                  {besoins.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="message" className="block text-sm font-semibold text-marine-800">Précisions</label>
                <textarea id="message" name="message" rows={4} placeholder="Contexte de votre demande" value={valeurs.message} onChange={changer} className={`${CHAMP} resize-y`} />
                <p className="mt-2 text-sm text-ardoise-400">Effectif, exercice en cours, échéance à tenir, retards à régulariser…</p>
              </div>
            </div>
            <label htmlFor="consentement" className="mt-6 flex items-start gap-3 text-sm text-ardoise-500">
              <input id="consentement" name="consentement" type="checkbox" required checked={valeurs.consentement} onChange={changer} className="mt-0.5 h-4 w-4 shrink-0 rounded border-ardoise-300 text-marine-800" />
              <span>J’autorise <span className="font-semibold text-marine-800">EKA CONSEIL</span> à utiliser ces informations pour répondre à ma demande, conformément à la loi 09-08.</span>
            </label>
            {erreur && <p role="alert" className="mt-6 rounded-lg bg-red-50 p-4 text-sm font-medium text-red-700">{erreur}</p>}
            {envoye && <p role="status" className="mt-6 rounded-lg bg-emerald-50 p-4 text-sm font-medium text-emerald-800">Demande enregistrée. Un consultant du cabinet revient vers vous sous 24 heures ouvrées pour planifier le premier entretien de diagnostic.</p>}
            <button type="submit" className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-marine-800 px-7 py-3.5 text-base font-semibold text-white shadow-card transition hover:bg-marine-700">
              Demander ma consultation <Icone nom="arrow" className="h-4 w-4" trait={2} />
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}
