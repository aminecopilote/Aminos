import { Link, useParams } from 'react-router-dom'
import Icone from '../components/Icone.jsx'
import * as api from '../data/api.js'
import { dateCourte } from '../data/format.js'
import { Chargement, ETATS_DOSSIER, Entete, Jauge, POLES, Panneau, Pastille } from './ui.jsx'
import useDonnees from './useDonnees.js'

function RetourDossiers() {
  return (
    <Link to="/espace-client/dossiers" className="inline-flex items-center gap-1.5 text-sm font-medium text-ardoise-500 hover:text-marine-800">
      <Icone nom="arrow" className="h-4 w-4 rotate-180" trait={2} /> Tous les dossiers
    </Link>
  )
}

export default function Dossier() {
  const { id } = useParams()
  const { chargement, donnees: d } = useDonnees(() => api.getDossier(id), [id])
  if (chargement) return <Chargement />
  if (!d) {
    return (
      <div className="space-y-6">
        <RetourDossiers />
        <Entete titre="Dossier introuvable" chapeau={`Aucun dossier ne porte la référence ${id}.`} />
      </div>
    )
  }

  const attendues = d.pieces.filter((p) => p.etat === 'attendu').length
  return (
    <div className="space-y-6">
      <RetourDossiers />
      <Entete titre={d.intitule} chapeau={`${POLES[d.pole]} · réf. ${d.id} · responsable : ${d.responsable}`} action={<Pastille ton={ETATS_DOSSIER[d.etat].ton}>{ETATS_DOSSIER[d.etat].libelle}</Pastille>} />
      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.6fr]">
        <Panneau titre="Étapes du dossier" soustitre="Chaque étape porte sa date de réalisation ou sa date cible">
          <ol className="px-6 py-6">
            {d.etapes.map((e, i) => {
              const fait = e.etat === 'termine'
              const actif = e.etat === 'enCours'
              const dernier = i === d.etapes.length - 1
              return (
                <li key={e.titre} className="relative flex gap-4 pb-6 last:pb-0">
                  {!dernier && <span className={`absolute left-[11px] top-6 h-full w-px ${fait ? 'bg-marine-300' : 'bg-ardoise-200'}`} />}
                  <span className={`relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ring-4 ring-white ${fait ? 'bg-etat-bon text-white' : actif ? 'bg-marine-800 text-white' : 'bg-ardoise-200 text-ardoise-500'}`}>
                    {fait ? <Icone nom="check" className="h-3.5 w-3.5" trait={3} /> : <span className="text-[0.65rem] font-bold tabular-nums">{i + 1}</span>}
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <p className={`text-sm ${actif ? 'font-semibold text-marine-900' : 'font-medium text-marine-800'}`}>{e.titre}</p>
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ardoise-400">
                      <span>{fait ? 'Réalisée le' : 'Prévue le'} {dateCourte(e.date)}</span>
                      <Pastille ton={fait ? 'bon' : 'neutre'}>{fait ? 'Terminée' : actif ? 'En cours' : 'À venir'}</Pastille>
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>
        </Panneau>
        <div className="space-y-6">
          <Panneau titre="Avancement">
            <div className="space-y-4 px-6 py-6">
              <Jauge valeur={d.avancement} libelle="Étapes réalisées" />
              <dl className="space-y-3 border-t border-ardoise-100 pt-4 text-sm">
                <div className="flex justify-between gap-4"><dt className="text-ardoise-500">Échéance</dt><dd className="font-semibold text-marine-900">{dateCourte(d.echeance)}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-ardoise-500">Dernière mise à jour</dt><dd className="font-semibold text-marine-900">{dateCourte(d.majLe)}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-ardoise-500">Responsable</dt><dd className="font-semibold text-marine-900">{d.responsable}</dd></div>
              </dl>
            </div>
          </Panneau>
          <Panneau titre="Pièces du dossier" soustitre={attendues ? `${attendues} pièce(s) attendue(s) de votre part` : 'Toutes les pièces sont réceptionnées'}>
            <ul className="divide-y divide-ardoise-100">
              {d.pieces.map((p) => (
                <li key={p.intitule} className="flex items-center justify-between gap-3 px-6 py-4">
                  <span className="min-w-0 text-sm text-ardoise-600">{p.intitule}</span>
                  <Pastille ton={p.etat === 'recu' ? 'bon' : 'serieux'}>{p.etat === 'recu' ? 'Reçue' : 'Attendue'}</Pastille>
                </li>
              ))}
            </ul>
          </Panneau>
        </div>
      </div>
    </div>
  )
}
