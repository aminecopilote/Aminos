import Icone from '../components/Icone.jsx'

export const ETATS_DOSSIER = {
  termine: { libelle: 'Terminé', ton: 'bon' },
  aValider: { libelle: 'À valider', ton: 'attention' },
  enCours: { libelle: 'En cours', ton: 'neutre' },
  attentePieces: { libelle: 'Pièces attendues', ton: 'serieux' },
}
export const POLES = { comptabilite: 'Comptabilité & Fiscalité', paie: 'Paie & RH', juridique: 'Juridique', marques: 'Marques' }
export const ETATS_ECHEANCE = {
  tenue: { ton: 'bon', libelle: 'Tenue' },
  aVenir: { ton: 'neutre', libelle: 'À venir' },
  urgente: { ton: 'attention', libelle: 'À traiter' },
}

const TONS = {
  bon: ['bg-etat-bon', 'bg-emerald-50 ring-emerald-100'],
  attention: ['bg-etat-attention', 'bg-amber-50 ring-amber-100'],
  serieux: ['bg-etat-serieux', 'bg-orange-50 ring-orange-100'],
  critique: ['bg-etat-critique', 'bg-red-50 ring-red-100'],
  neutre: ['bg-marine-500', 'bg-marine-50 ring-marine-100'],
}

// Pastille d'état : point coloré + libellé, texte en encre neutre.
export function Pastille({ ton, children }) {
  const [point, fond] = TONS[ton] || TONS.neutre
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold text-ardoise-700 ring-1 ring-inset ${fond}`}>
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${point}`} />
      {children}
    </span>
  )
}

// Jauge : piste en teinte claire de la même rampe que le remplissage.
export function Jauge({ valeur, libelle = 'Avancement' }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs text-ardoise-500">{libelle}</span>
        <span className="text-xs font-semibold tabular-nums text-marine-800">{valeur} %</span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-marine-100" role="progressbar" aria-valuenow={valeur} aria-valuemin={0} aria-valuemax={100} aria-label={libelle}>
        <div className="h-full rounded-full bg-marine-600" style={{ width: `${valeur}%` }} />
      </div>
    </div>
  )
}

export function Panneau({ titre, soustitre, action, children }) {
  return (
    <section className="min-w-0 rounded-2xl border border-ardoise-100 bg-white shadow-card">
      {titre && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-ardoise-100 px-6 py-5">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-marine-900">{titre}</h2>
            {soustitre && <p className="mt-1 text-sm text-ardoise-500">{soustitre}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

// Tuile d'indicateur : valeur en chiffres proportionnels.
export function Tuile({ libelle, valeur, unite, note }) {
  return (
    <div className="rounded-2xl border border-ardoise-100 bg-white p-5 shadow-card">
      <p className="text-sm text-ardoise-500">{libelle}</p>
      <p className="mt-2 flex items-baseline gap-1.5 text-3xl font-semibold text-marine-900">
        {valeur}
        {unite && <span className="text-base font-medium text-ardoise-400">{unite}</span>}
      </p>
      <p className="mt-2.5 text-xs text-ardoise-400">{note}</p>
    </div>
  )
}

export function Entete({ titre, chapeau, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-marine-900">{titre}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ardoise-500">{chapeau}</p>
      </div>
      {action}
    </div>
  )
}

export function Chargement() {
  return <p className="py-16 text-center text-sm text-ardoise-400" role="status">Chargement…</p>
}

export function LienFleche({ children, ...props }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-marine-800" {...props}>
      {children} <Icone nom="arrow" className="h-4 w-4" trait={2} />
    </span>
  )
}
