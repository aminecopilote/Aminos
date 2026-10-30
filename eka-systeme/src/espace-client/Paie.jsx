import * as api from '../data/api.js'
import { mad, nombre } from '../data/format.js'
import Histogramme from './Histogramme.jsx'
import { Chargement, Entete, Panneau, Pastille, Tuile } from './ui.jsx'
import useDonnees from './useDonnees.js'

export default function Paie() {
  const { donnees: paie } = useDonnees(api.getPaie)
  if (!paie) return <Chargement />
  const s = paie.synthese
  const lignesSynthese = [
    ['Salaire brut global', s.brut], ['Cotisations salariales', s.cotisationsSalariales],
    ['Cotisations patronales', s.cotisationsPatronales], ['IR retenu à la source', s.irRetenu],
    ['Net à payer', s.net], ['Coût employeur', s.brut + s.cotisationsPatronales],
  ]
  return (
    <div className="space-y-6">
      <Entete titre="Paie & RH" chapeau={`Cycle de paie d’${paie.periode.toLowerCase()} — ${s.bulletins} bulletins pour un effectif de ${s.effectif} salariés. Les déclarations CNSS et AMO sont produites depuis ces mêmes données.`} action={<Pastille ton="attention">Bulletins à valider</Pastille>} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tuile libelle="Masse salariale brute" valeur={nombre(s.brut)} unite="MAD" note="+3 % vs septembre" />
        <Tuile libelle="Cotisations patronales" valeur={nombre(s.cotisationsPatronales)} unite="MAD" note="CNSS, AMO, taxe de formation" />
        <Tuile libelle="IR retenu à la source" valeur={nombre(s.irRetenu)} unite="MAD" note="À verser avant le 31/10" />
        <Tuile libelle="Net à payer" valeur={nombre(s.net)} unite="MAD" note="Ordre de virement prêt" />
      </div>
      <Panneau titre="Masse salariale brute par mois" soustitre="Six derniers mois, en dirhams — survolez une barre pour le détail">
        <div className="px-6 py-6"><Histogramme donnees={paie.masseSalariale} /></div>
      </Panneau>
      <Panneau titre="Synthèse du mois" soustitre={paie.periode}>
        <dl className="grid gap-px bg-ardoise-100 sm:grid-cols-2 lg:grid-cols-3">
          {lignesSynthese.map(([l, v]) => (
            <div key={l} className="bg-white px-6 py-5"><dt className="text-sm text-ardoise-500">{l}</dt><dd className="mt-1.5 text-lg font-semibold tabular-nums text-marine-900">{mad(v)}</dd></div>
          ))}
        </dl>
      </Panneau>
      <Panneau titre="Bulletins d’octobre" soustitre={`${paie.salaries.length} premiers salariés sur ${s.effectif} — export complet disponible`}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-sm">
            <thead>
              <tr className="border-b border-ardoise-100 text-left text-xs font-semibold uppercase tracking-wide text-ardoise-400">
                <th scope="col" className="px-6 py-3">Matricule</th><th scope="col" className="px-6 py-3">Salarié</th><th scope="col" className="px-6 py-3">Poste</th>
                <th scope="col" className="px-6 py-3">Contrat</th><th scope="col" className="px-6 py-3 text-right">Brut</th><th scope="col" className="px-6 py-3 text-right">Net</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ardoise-100">
              {paie.salaries.map((x) => (
                <tr key={x.matricule}>
                  <td className="px-6 py-4 tabular-nums text-ardoise-400">{x.matricule}</td>
                  <td className="px-6 py-4 font-medium text-marine-900">{x.nom}</td>
                  <td className="px-6 py-4 text-ardoise-500">{x.poste}</td>
                  <td className="px-6 py-4"><span className="rounded-full bg-ardoise-100 px-2 py-0.5 text-xs font-semibold text-ardoise-600">{x.contrat}</span></td>
                  <td className="px-6 py-4 text-right tabular-nums text-ardoise-600">{nombre(x.brut)}</td>
                  <td className="px-6 py-4 text-right font-semibold tabular-nums text-marine-900">{nombre(x.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panneau>
    </div>
  )
}
