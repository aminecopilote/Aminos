import * as api from '../data/api.js'
import { dateCourte, joursRestants, mad } from '../data/format.js'
import { Chargement, ETATS_ECHEANCE, Entete, Panneau, Pastille } from './ui.jsx'
import useDonnees from './useDonnees.js'

function TableauEcheances({ lignes, avecDelai }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[42rem] text-sm">
        <thead>
          <tr className="border-b border-ardoise-100 text-left text-xs font-semibold uppercase tracking-wide text-ardoise-400">
            <th scope="col" className="px-6 py-3">Obligation</th><th scope="col" className="px-6 py-3">Administration</th>
            <th scope="col" className="px-6 py-3">Échéance</th><th scope="col" className="px-6 py-3 text-right">Montant</th><th scope="col" className="px-6 py-3">État</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ardoise-100">
          {lignes.map((e) => (
            <tr key={e.id}>
              <td className="px-6 py-4 font-medium text-marine-900">{e.intitule}</td>
              <td className="px-6 py-4 text-ardoise-500">{e.administration}</td>
              <td className="px-6 py-4 tabular-nums text-ardoise-600">{dateCourte(e.date)}{avecDelai && <span className="ml-2 text-xs text-ardoise-400">dans {joursRestants(e.date)} j</span>}</td>
              <td className="px-6 py-4 text-right tabular-nums text-marine-900">{mad(e.montant)}</td>
              <td className="px-6 py-4"><Pastille ton={ETATS_ECHEANCE[e.etat].ton}>{ETATS_ECHEANCE[e.etat].libelle}</Pastille></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Echeancier() {
  const { donnees: echeances } = useDonnees(api.getEcheances)
  if (!echeances) return <Chargement />
  const parDate = (a, b) => a.date.localeCompare(b.date)
  const aVenir = echeances.filter((e) => e.etat !== 'tenue').sort(parDate)
  const tenues = echeances.filter((e) => e.etat === 'tenue').sort(parDate)
  const total = aVenir.reduce((s, e) => s + (e.montant || 0), 0)
  return (
    <div className="space-y-6">
      <Entete titre="Échéancier réglementaire" chapeau="Vos obligations fiscales, sociales et juridiques calendées. Une alerte vous parvient sept jours avant chaque échéance." />
      <Panneau titre="À venir" soustitre={`${aVenir.length} obligations · ${mad(total)} à décaisser d’ici le 31/12/2026`}><TableauEcheances lignes={aVenir} avecDelai /></Panneau>
      <Panneau titre="Déjà tenues" soustitre="Accusés de dépôt disponibles dans le coffre-fort"><TableauEcheances lignes={tenues} /></Panneau>
    </div>
  )
}
