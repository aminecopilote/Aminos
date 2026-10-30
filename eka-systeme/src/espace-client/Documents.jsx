import Icone from '../components/Icone.jsx'
import * as api from '../data/api.js'
import { dateCourte } from '../data/format.js'
import { Chargement, Entete, Panneau } from './ui.jsx'
import useDonnees from './useDonnees.js'

export default function Documents() {
  const { donnees } = useDonnees(api.getDocuments)
  if (!donnees) return <Chargement />
  const total = donnees.categories.reduce((s, c) => s + c.total, 0)
  return (
    <div className="space-y-6">
      <Entete titre="Coffre-fort documentaire" chapeau="Statuts, procès-verbaux, contrats de travail, bulletins et accusés de dépôt, archivés et horodatés. Les accès sont nominatifs et tracés." />
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-marine-800 px-3.5 py-1.5 text-sm font-medium text-white">Toutes · {total}</span>
        {donnees.categories.map((c) => (
          <span key={c.libelle} className="rounded-full bg-white px-3.5 py-1.5 text-sm font-medium text-ardoise-600 ring-1 ring-inset ring-ardoise-200">{c.libelle} · {c.total}</span>
        ))}
      </div>
      <Panneau titre="Dépôts récents" soustitre={`${donnees.recents.length} documents affichés`}>
        <ul className="divide-y divide-ardoise-100">
          {donnees.recents.map((doc) => (
            <li key={doc.id} className="flex items-center gap-4 px-6 py-4">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-marine-50 text-marine-700"><Icone nom="document" className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-marine-900">{doc.nom}</p>
                <p className="mt-1 text-xs text-ardoise-400">{doc.categorie} · {doc.poids} · déposé le {dateCourte(doc.depose)} par EKA CONSEIL</p>
              </div>
              <span className="shrink-0 text-sm font-semibold text-ardoise-400" title="Téléchargement disponible avec le backend">Télécharger</span>
            </li>
          ))}
        </ul>
      </Panneau>
    </div>
  )
}
