import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icone from '../components/Icone.jsx'
import { apercuDossiers, atouts, chiffresPlateforme, etapesMethode, faq, indicateurs, services } from './contenu.js'

const Etiquette = ({ children, sombre }) => (
  <span className={`inline-flex items-center rounded-full px-3.5 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] ring-1 ring-inset ${sombre ? 'bg-white/10 text-marine-50 ring-white/20' : 'bg-marine-50 text-marine-700 ring-marine-100'}`}>
    {children}
  </span>
)

const BoutonOr = ({ href, children }) => (
  <a href={href} className="inline-flex items-center justify-center gap-2 rounded-lg bg-or-500 px-7 py-3.5 text-base font-semibold text-marine-900 shadow-card transition hover:bg-or-400">
    {children} <Icone nom="arrow" className="h-4 w-4" trait={2} />
  </a>
)

const TONS_APERCU = {
  bon: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  or: 'bg-or-50 text-or-700 ring-or-200',
  marine: 'bg-marine-50 text-marine-700 ring-marine-200',
}

export function Hero() {
  return (
    <section id="accueil" className="relative overflow-hidden bg-marine-900">
      <div className="trame absolute inset-0 opacity-60" aria-hidden="true" />
      <div className="absolute -right-32 -top-40 h-[32rem] w-[32rem] rounded-full bg-marine-700/40 blur-3xl" aria-hidden="true" />
      <div className="absolute -bottom-48 left-1/4 h-[28rem] w-[28rem] rounded-full bg-or-500/10 blur-3xl" aria-hidden="true" />

      <div className="wrap relative py-20 lg:py-28">
        <div className="grid items-center gap-16 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-marine-50 ring-1 ring-inset ring-white/20">
              <span className="h-1.5 w-1.5 rounded-full bg-or-400" /> Cabinet d’expertise — Casablanca
            </span>
            <h1 className="mt-7 text-4xl leading-[1.1] text-white sm:text-5xl lg:text-[3.4rem]">
              Votre entreprise accompagnée,{' '}
              <span className="relative whitespace-nowrap">
                <span className="relative z-10 text-or-300">sécurisée</span>
                <span className="absolute inset-x-0 bottom-1 z-0 h-3 bg-or-500/20" aria-hidden="true" />
              </span>{' '}
              et pilotée de bout en bout.
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-relaxed text-marine-100">
              EKA CONSEIL réunit la rigueur du conseil juridique, comptable et social et l’efficacité d’outils digitaux développés en interne. Vous déléguez vos obligations administratives ; vous gardez la visibilité complète sur vos dossiers.
            </p>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row">
              <BoutonOr href="#services">Découvrir nos services</BoutonOr>
              <a href="#contact" className="inline-flex items-center justify-center gap-2 rounded-lg px-7 py-3.5 text-base font-semibold text-white ring-1 ring-inset ring-white/35 transition hover:bg-white/10 hover:ring-white/60">Demander une consultation</a>
            </div>
            <ul className="mt-12 grid gap-3 sm:grid-cols-3">
              {['Interlocuteur unique dédié', 'Honoraires forfaitaires annoncés', 'Échéances fiscales et sociales tenues'].map((t) => (
                <li key={t} className="flex items-start gap-2.5 text-sm text-marine-100"><Icone nom="check" className="mt-0.5 h-4 w-4 shrink-0 text-or-400" trait={2.4} /> {t}</li>
              ))}
            </ul>
          </div>

          <div className="lg:pl-6">
            <div className="rounded-2xl border border-white/10 bg-white/95 p-6 shadow-float sm:p-7">
              <div className="flex items-center justify-between gap-4 border-b border-ardoise-100 pb-5">
                <div>
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-ardoise-400">EKA SYSTÈME</p>
                  <p className="mt-1.5 text-base font-semibold text-marine-900">Suivi de vos dossiers</p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> À jour
                </span>
              </div>
              <ul className="divide-y divide-ardoise-100">
                {apercuDossiers.map(([intitule, statut, ton]) => (
                  <li key={intitule} className="flex items-center justify-between gap-4 py-4">
                    <span className="min-w-0 text-sm font-medium text-marine-800">{intitule}</span>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${TONS_APERCU[ton]}`}>{statut}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-5 flex items-center gap-3 rounded-xl bg-marine-50 p-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-marine-800 text-white"><Icone nom="bolt" className="h-5 w-5" /></span>
                <p className="text-sm leading-snug text-marine-700"><span className="font-semibold text-marine-900">Prochaine échéance :</span> télédéclaration TVA — fichier XML Simpl-TVA généré automatiquement.</p>
              </div>
              <Link to="/espace-client" className="mt-4 block text-center text-xs font-semibold text-marine-700 underline decoration-or-400 underline-offset-4 hover:text-marine-900">
                Ouvrir la démonstration de l’espace client
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export function Indicateurs() {
  return (
    <section className="border-b border-ardoise-100 bg-white">
      <div className="wrap py-10 lg:py-12">
        <dl className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {indicateurs.map(([valeur, libelle]) => (
            <div key={libelle} className="flex flex-col-reverse border-l-2 border-or-400 pl-4">
              <dt className="mt-1.5 text-sm leading-snug text-ardoise-500">{libelle}</dt>
              <dd className="text-2xl font-bold tabular-nums text-marine-900 sm:text-3xl">{valeur}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

export function Services() {
  return (
    <section id="services" className="scroll-mt-28 bg-ardoise-50 py-20 lg:py-28">
      <div className="wrap">
        <Etiquette>Nos services</Etiquette>
        <h2 className="mt-5 max-w-3xl text-3xl leading-[1.15] sm:text-4xl lg:text-[2.75rem]">Cinq expertises, un seul cabinet responsable de vos obligations.</h2>
        <p className="mt-5 max-w-3xl text-lg leading-relaxed text-ardoise-500">De la constitution de votre société à la gestion quotidienne de vos dossiers, nous couvrons l’intégralité du cycle administratif, fiscal, social et juridique de votre entreprise.</p>

        <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <article key={s.titre} className={`group flex flex-col rounded-2xl border p-7 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover lg:p-8 ${s.vedette ? 'border-marine-200 bg-marine-50/40 lg:col-span-2' : 'border-ardoise-100 bg-white'}`}>
              <div className="flex items-start justify-between gap-4">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-marine-800 text-white transition group-hover:bg-marine-900"><Icone nom={s.icone} /></span>
                {s.vedette && <span className="rounded-full bg-marine-800 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-white">Mission récurrente</span>}
              </div>
              <h3 className="mt-6 text-xl font-semibold text-marine-900">{s.titre}</h3>
              <p className="mt-2 text-sm font-semibold text-or-600">{s.accroche}</p>
              <p className="mt-4 max-w-2xl text-[0.95rem] leading-relaxed text-ardoise-500">{s.texte}</p>
              <ul className={`mt-6 grid gap-2.5 border-t border-ardoise-100 pt-6 ${s.vedette ? 'sm:grid-cols-2' : ''}`}>
                {s.points.map((p) => (
                  <li key={p} className="flex items-start gap-2.5 text-sm text-ardoise-600"><Icone nom="check" className="mt-0.5 h-4 w-4 shrink-0 text-marine-500" trait={2.4} /><span className="min-w-0">{p}</span></li>
                ))}
              </ul>
              <div className="mt-auto flex flex-wrap items-center justify-between gap-4 pt-7">
                <p className="flex items-center gap-2 text-xs font-semibold text-marine-700"><Icone nom="clock" className="h-4 w-4 text-or-500" /> {s.delai}</p>
                <a href="#contact" className="inline-flex items-center gap-1.5 text-sm font-semibold text-marine-800 underline decoration-or-400 decoration-2 underline-offset-4 hover:text-marine-600">Étudier mon dossier <Icone nom="arrow" className="h-4 w-4" trait={2} /></a>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export function ValeurAjoutee() {
  return (
    <section id="valeur-ajoutee" className="relative scroll-mt-28 overflow-hidden bg-marine-900 py-20 lg:py-28">
      <div className="trame absolute inset-0 opacity-50" aria-hidden="true" />
      <div className="absolute -left-40 top-1/3 h-[30rem] w-[30rem] rounded-full bg-marine-700/40 blur-3xl" aria-hidden="true" />
      <div className="wrap relative">
        <div className="grid gap-16 lg:grid-cols-[1fr_1.05fr] lg:items-start">
          <div>
            <Etiquette sombre>Notre valeur ajoutée</Etiquette>
            <h2 className="mt-5 text-3xl leading-[1.15] text-white sm:text-4xl lg:text-[2.75rem]">Le conseil d’un cabinet, la transparence d’une plateforme : <span className="text-or-300">EKA SYSTÈME</span>.</h2>
            <p className="mt-5 text-lg leading-relaxed text-marine-100">Nous ne nous contentons pas du conseil classique. Nous développons nos propres interfaces de gestion et nos workflows internes pour industrialiser ce qui doit l’être — et garder l’expertise humaine là où elle crée de la valeur.</p>
            <p className="mt-6 max-w-2xl leading-relaxed text-marine-200">Résultat : vos dossiers juridiques, comptables et de paie avancent plus vite, les statuts sont visibles en temps réel, et chaque document produit reste disponible au même endroit.</p>
            <dl className="mt-10 grid grid-cols-3 gap-6 border-t border-white/10 pt-8">
              {chiffresPlateforme.map(([valeur, libelle]) => (
                <div key={libelle} className="flex flex-col-reverse">
                  <dt className="mt-1.5 text-xs leading-snug text-marine-300 sm:text-sm">{libelle}</dt>
                  <dd className="text-2xl font-bold tabular-nums text-or-300 sm:text-3xl">{valeur}</dd>
                </div>
              ))}
            </dl>
            <Link to="/espace-client" className="mt-10 inline-flex items-center gap-2 rounded-lg bg-or-500 px-7 py-3.5 text-base font-semibold text-marine-900 shadow-card transition hover:bg-or-400">
              Voir la plateforme en démonstration <Icone nom="arrow" className="h-4 w-4" trait={2} />
            </Link>
          </div>
          <ul className="grid gap-5 sm:grid-cols-2">
            {atouts.map((a) => (
              <li key={a.titre} className="rounded-2xl border border-white/10 bg-white/[0.06] p-6 transition hover:border-or-400/40 hover:bg-white/[0.09]">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-or-500/15 text-or-300 ring-1 ring-inset ring-or-400/30"><Icone nom={a.icone} className="h-5 w-5" /></span>
                <h3 className="mt-5 text-base font-semibold text-white">{a.titre}</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-marine-200">{a.texte}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export function Methode() {
  return (
    <section id="methode" className="scroll-mt-28 bg-white py-20 lg:py-28">
      <div className="wrap">
        <Etiquette>Notre méthode</Etiquette>
        <h2 className="mt-5 max-w-3xl text-3xl leading-[1.15] sm:text-4xl lg:text-[2.75rem]">Une prise en charge cadrée, du premier entretien au pilotage continu.</h2>
        <p className="mt-5 max-w-3xl text-lg leading-relaxed text-ardoise-500">Chaque mission suit le même déroulé. Vous savez à l’avance qui fait quoi, dans quel délai et pour quel honoraire.</p>
        <ol className="mt-14 grid gap-px overflow-hidden rounded-2xl bg-ardoise-100 sm:grid-cols-2 lg:grid-cols-4">
          {etapesMethode.map(([titre, texte], i) => (
            <li key={titre} className="bg-white p-7 lg:p-8">
              <div className="flex items-baseline gap-3"><span className="text-sm font-bold tabular-nums text-or-500">{String(i + 1).padStart(2, '0')}</span><span className="h-px flex-1 bg-ardoise-200" /></div>
              <h3 className="mt-5 text-lg font-semibold">{titre}</h3>
              <p className="mt-3 text-sm leading-relaxed text-ardoise-500">{texte}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

export function Faq() {
  const [ouverte, setOuverte] = useState(0)
  return (
    <section id="faq" className="scroll-mt-28 bg-ardoise-50 py-20 lg:py-28">
      <div className="wrap">
        <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
          <div>
            <Etiquette>Questions fréquentes</Etiquette>
            <h2 className="mt-5 text-3xl leading-[1.15] sm:text-4xl">Les réponses aux questions que l’on nous pose avant d’engager une mission.</h2>
            <p className="mt-5 text-lg leading-relaxed text-ardoise-500">Une question qui n’apparaît pas ici ? Posez-la directement, la réponse vous parvient sous 24 heures ouvrées.</p>
          </div>
          <div className="divide-y divide-ardoise-200 border-y border-ardoise-200">
            {faq.map(([question, reponse], i) => {
              const actif = ouverte === i
              return (
                <div key={question}>
                  <h3>
                    <button type="button" id={`faq-q-${i}`} aria-expanded={actif} aria-controls={`faq-r-${i}`} onClick={() => setOuverte(actif ? -1 : i)} className="flex w-full items-start justify-between gap-6 py-6 text-left">
                      <span className="text-base font-semibold text-marine-900 sm:text-lg">{question}</span>
                      <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-1 ring-inset transition-all duration-300 ${actif ? 'rotate-180 bg-marine-800 text-white ring-marine-800' : 'bg-white text-marine-700 ring-ardoise-200'}`}>
                        <Icone nom="chevron" className="h-4 w-4" trait={2} />
                      </span>
                    </button>
                  </h3>
                  <div id={`faq-r-${i}`} role="region" aria-labelledby={`faq-q-${i}`} hidden={!actif} className="pb-7 pr-12">
                    <p className="text-[0.95rem] leading-relaxed text-ardoise-500">{reponse}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}

export function Relance({ telephone }) {
  return (
    <section className="bg-ardoise-50 pb-20 lg:pb-28">
      <div className="wrap">
        <div className="relative overflow-hidden rounded-3xl bg-marine-800 px-7 py-14 sm:px-12 lg:px-16">
          <div className="trame absolute inset-0 opacity-40" aria-hidden="true" />
          <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-or-500/15 blur-3xl" aria-hidden="true" />
          <div className="relative max-w-3xl">
            <h2 className="text-3xl leading-tight text-white sm:text-4xl">Vous avez une échéance à tenir ou des retards à régulariser ?</h2>
            <p className="mt-5 text-lg leading-relaxed text-marine-100">Nos équipes réalisent un audit de conformité de votre dossier et vous remettent un plan de régularisation chiffré, avec un calendrier ferme.</p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <BoutonOr href="#contact">Demander un audit de conformité</BoutonOr>
              <span className="inline-flex items-center justify-center gap-2 rounded-lg px-7 py-3.5 text-base font-semibold text-white ring-1 ring-inset ring-white/35">{telephone}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
