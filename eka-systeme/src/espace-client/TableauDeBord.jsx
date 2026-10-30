import { Link } from 'react-router-dom'
import * as api from '../data/api.js'
import { dateCourte, joursRestants, mad, nombre } from '../data/format.js'
import Histogramme from './Histogramme.jsx'
import { useSession } from './session.jsx'
import { Chargement, ETATS_DOSSIER, ETATS_ECHEANCE, Entete, Jauge, LienFleche, POLES, Panneau, Pastille, Tuile } from './ui.jsx'
import useDonnees from './useDonnees.js'

const charger = () => Promise.all([api.getDossiers(), api.getEcheances(), api.getPaie(), api.getActivite()])

export default function TableauDeBord() {
  const { client } = useSession()
  const { donnees } = useDonnees(charger)
  if (!donnees) return <Chargement />
  const [dossiers, echeances, paie, activite] = donnees

  const aVenir = echeances.filter((e) => e.etat !== 'tenue').sort((a, b) => a.date.localeCompare(b.date))
  const enCours = dossiers.filter((d) => d.avancement < 100)
  const enAttente = enCours.filter((d) => d.etat === 'attentePieces').length
  const prochaine = aVenir[0]
  const mois = paie.masseSalariale
  const variation = Math.round(((mois.at(-1).brut - mois.at(-2).brut) / mois.at(-2).brut) * 100)

  return (
    <div className="space-y-6">
      <Entete titre={`Bonjour ${client.utilisateur.prenom}`} chapeau={`État de vos obligations et de vos dossiers au 17 octobre 2026. Votre responsable de mission est ${client.interlocuteur.nom}.`} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tuile libelle="Échéances sous 30 jours" valeur={aVenir.filter((e) => joursRestants(e.date) <= 30).length} note="Aucune échéance dépassée" />
        <Tuile libelle="Dossiers en cours" valeur={enCours.length} note={`dont ${enAttente} en attente de pièces`} />
        <Tuile libelle={`Masse salariale — ${paie.periode.split(' ')[0].toLowerCase()}`} valeur={nombre(paie.synthese.brut)} unite="MAD" note={`${variation >= 0 ? '+' : ''}${variation} % vs mois précédent`} />
        <Tuile libelle="Bulletins du mois" valeur={paie.synthese.bulletins} note={`Effectif : ${paie.synthese.effectif} salariés`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panneau titre="Prochaine échéance" soustitre="Obligation la plus proche, toutes administrations confondues">
          <div className="flex flex-wrap items-center gap-8 px-6 py-6">
            <div>
              <p className="text-5xl font-semibold leading-none text-marine-900">{joursRestants(prochaine.date)}</p>
              <p className="mt-2 text-sm text-ardoise-500">jours restants</p>
            </div>
            <div className="min-w-0 flex-1">
              <Pastille ton={ETATS_ECHEANCE[prochaine.etat].ton}>{ETATS_ECHEANCE[prochaine.etat].libelle}</Pastille>
              <p className="mt-3 text-base font-semibold text-marine-900">{prochaine.intitule}</p>
              <p className="mt-1.5 text-sm text-ardoise-500">{prochaine.administration} · échéance du {dateCourte(prochaine.date)}{prochaine.montant ? ` · ${mad(prochaine.montant)}` : ''}</p>
              <Link to="echeancier" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-marine-800 underline decoration-or-400 decoration-2 underline-offset-4">Voir tout l’échéancier</Link>
            </div>
          </div>
        </Panneau>
        <Panneau titre="Échéances à venir" soustitre="Fiscales, sociales et juridiques">
          <ul className="divide-y divide-ardoise-100">
            {aVenir.slice(0, 4).map((e) => (
              <li key={e.id} className="flex items-start justify-between gap-4 px-6 py-4">
                <div className="min-w-0"><p className="text-sm font-medium text-marine-900">{e.intitule}</p><p className="mt-1 text-xs text-ardoise-400">{e.administration} · {dateCourte(e.date)}</p></div>
                <div className="shrink-0 text-right">
                  <Pastille ton={ETATS_ECHEANCE[e.etat].ton}>{joursRestants(e.date)} j</Pastille>
                  {e.montant && <p className="mt-1.5 text-xs tabular-nums text-ardoise-500">{mad(e.montant)}</p>}
                </div>
              </li>
            ))}
          </ul>
        </Panneau>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panneau titre="Masse salariale brute par mois" soustitre="Six derniers mois, en dirhams — survolez une barre pour le détail">
          <div className="px-6 py-6"><Histogramme donnees={mois} /></div>
        </Panneau>
        <Panneau titre="Activité récente" soustitre="Interventions du cabinet sur vos dossiers">
          <ol className="divide-y divide-ardoise-100">
            {activite.map((a) => (
              <li key={a.date + a.texte} className="px-6 py-4"><p className="text-sm leading-relaxed text-ardoise-600">{a.texte}</p><p className="mt-1.5 text-xs text-ardoise-400">{dateCourte(a.date)} · {a.par}</p></li>
            ))}
          </ol>
        </Panneau>
      </div>

      <Panneau titre="Dossiers en cours" soustitre={`${enCours.length} dossiers suivis par le cabinet`} action={<Link to="dossiers"><LienFleche>Tous les dossiers</LienFleche></Link>}>
        <ul className="divide-y divide-ardoise-100">
          {enCours.map((d) => (
            <li key={d.id} className="grid gap-4 px-6 py-5 sm:grid-cols-[1.6fr_0.8fr_0.9fr] sm:items-center">
              <div className="min-w-0">
                <Link to={`dossiers/${d.id}`} className="text-sm font-semibold text-marine-900 hover:text-marine-600">{d.intitule}</Link>
                <p className="mt-1 text-xs text-ardoise-400">{POLES[d.pole]} · {d.responsable} · échéance {dateCourte(d.echeance)}</p>
              </div>
              <div><Pastille ton={ETATS_DOSSIER[d.etat].ton}>{ETATS_DOSSIER[d.etat].libelle}</Pastille></div>
              <Jauge valeur={d.avancement} />
            </li>
          ))}
        </ul>
      </Panneau>
    </div>
  )
}
