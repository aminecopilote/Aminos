import { Link } from 'react-router-dom'
import * as api from '../data/api.js'
import { dateCourte } from '../data/format.js'
import { Chargement, ETATS_DOSSIER, Entete, Jauge, POLES, Panneau, Pastille } from './ui.jsx'
import useDonnees from './useDonnees.js'

export default function Dossiers() {
  const { donnees: dossiers } = useDonnees(api.getDossiers)
  if (!dossiers) return <Chargement />
  return (
    <div className="space-y-6">
      <Entete titre="Mes dossiers" chapeau="Chaque dossier porte son étape en cours, son responsable au cabinet et sa date d’échéance. Ouvrez-en un pour voir le détail des étapes et les pièces attendues." />
      <Panneau>
        <ul className="divide-y divide-ardoise-100">
          {dossiers.map((d) => (
            <li key={d.id} className="grid gap-4 px-6 py-5 transition hover:bg-ardoise-50/60 lg:grid-cols-[1.7fr_0.9fr_0.7fr_0.9fr] lg:items-center">
              <div className="min-w-0">
                <Link to={d.id} className="text-sm font-semibold text-marine-900 hover:text-marine-600">{d.intitule}</Link>
                <p className="mt-1 text-xs text-ardoise-400">Réf. {d.id} · mise à jour le {dateCourte(d.majLe)}</p>
              </div>
              <p className="text-sm text-ardoise-600">{POLES[d.pole]}</p>
              <div><Pastille ton={ETATS_DOSSIER[d.etat].ton}>{ETATS_DOSSIER[d.etat].libelle}</Pastille></div>
              <Jauge valeur={d.avancement} libelle={`Échéance ${dateCourte(d.echeance)}`} />
            </li>
          ))}
        </ul>
      </Panneau>
    </div>
  )
}
