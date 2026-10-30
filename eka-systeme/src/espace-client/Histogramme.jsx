import { useState } from 'react'
import { nombre } from '../data/format.js'

// Histogramme à série unique : barres ≤ 24 px, sommet arrondi et pied carré,
// grille filaire 1 px, étiquette directe sur le seul dernier mois, infobulle au survol.
const W = 640, H = 280, L = 52, R = 12, HT = 28, HB = 36, BW = 24, RY = 4

export default function Histogramme({ donnees, max = 200000, pas = 50000 }) {
  const [actif, setActif] = useState(null)
  const largeur = W - L - R
  const hauteur = H - HT - HB
  const bande = largeur / donnees.length
  const baseY = HT + hauteur
  const y = (v) => baseY - (v / max) * hauteur
  const cx = (i) => L + bande * i + bande / 2
  const graduations = []
  for (let v = 0; v <= max; v += pas) graduations.push(v)

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-full" role="img" aria-label="Masse salariale brute des six derniers mois, en dirhams">
        {graduations.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#DCE0E8" strokeWidth="1" />
            <text x={L - 10} y={y(v) + 4} textAnchor="end" fill="#8D98AA" fontSize="11" style={{ fontVariantNumeric: 'tabular-nums' }}>{v === 0 ? '0' : `${Math.round(v / 1000)} k`}</text>
          </g>
        ))}
        {donnees.map((p, i) => {
          const x = cx(i) - BW / 2
          const couleur = actif === i ? '#132C46' : '#234B74'
          return (
            <g key={p.mois}>
              <rect x={x} y={y(p.brut)} width={BW} height={baseY - y(p.brut)} rx={RY} fill={couleur} />
              <rect x={x} y={baseY - RY} width={BW} height={RY} fill={couleur} />
              {i === donnees.length - 1 && (
                <text x={cx(i)} y={y(p.brut) - 10} textAnchor="middle" fill="#0D2033" fontSize="11" fontWeight="600" style={{ fontVariantNumeric: 'tabular-nums' }}>{nombre(p.brut)}</text>
              )}
              <text x={cx(i)} y={baseY + 20} textAnchor="middle" fill="#6B7687" fontSize="11">{p.mois}</text>
              <rect x={L + bande * i} y={HT} width={bande} height={hauteur} fill="transparent" tabIndex={0} role="button"
                aria-label={`${p.mois} : ${nombre(p.brut)} dirhams`}
                onMouseEnter={() => setActif(i)} onMouseLeave={() => setActif(null)} onFocus={() => setActif(i)} onBlur={() => setActif(null)} />
            </g>
          )
        })}
        <line x1={L} x2={W - R} y1={baseY} y2={baseY} stroke="#BCC4D1" strokeWidth="1" />
      </svg>
      {actif != null && (
        <div className="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded-lg bg-marine-900 px-3 py-2 text-xs text-white shadow-float"
          style={{ left: `${(cx(actif) / W) * 100}%`, top: `${(y(donnees[actif].brut) / H) * 100 - 3}%` }}>
          <p className="font-semibold">{donnees[actif].mois} 2026</p>
          <p className="mt-0.5 tabular-nums text-marine-200">{nombre(donnees[actif].brut)} MAD brut</p>
        </div>
      )}
      <details className="mt-4 border-t border-ardoise-100 pt-4">
        <summary className="cursor-pointer text-sm font-medium text-marine-800">Voir les données</summary>
        <table className="mt-3 w-full text-sm">
          <caption className="sr-only">Masse salariale brute mensuelle en dirhams</caption>
          <thead><tr className="text-left text-xs uppercase tracking-wide text-ardoise-400"><th scope="col" className="py-2 font-semibold">Mois</th><th scope="col" className="py-2 text-right font-semibold">Brut (MAD)</th></tr></thead>
          <tbody className="divide-y divide-ardoise-100">
            {donnees.map((p) => <tr key={p.mois}><td className="py-2 text-ardoise-600">{p.mois} 2026</td><td className="py-2 text-right tabular-nums text-marine-900">{nombre(p.brut)}</td></tr>)}
          </tbody>
        </table>
      </details>
    </div>
  )
}
