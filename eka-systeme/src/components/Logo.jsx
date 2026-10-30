import { Link } from 'react-router-dom'

// Monogramme EKA : « A » en or, décliné clair (vitrine) ou sur fond sombre.
export function Monogramme({ sombre = false }) {
  return (
    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-extrabold tracking-tight ${sombre ? 'bg-white text-marine-900' : 'bg-marine-800 text-white'}`}>
      EK<span className={sombre ? 'text-or-500' : 'text-or-400'}>A</span>
    </span>
  )
}

export default function Logo({ sombre = false, to = '/' }) {
  return (
    <Link to={to} className="flex items-center gap-3">
      <Monogramme sombre={sombre} />
      <span className="flex flex-col leading-none">
        <span className={`text-base font-extrabold tracking-tight ${sombre ? 'text-white' : 'text-marine-900'}`}>
          EKA <span className="font-semibold text-or-500">CONSEIL</span>
        </span>
        <span className={`mt-1 whitespace-nowrap text-[0.65rem] font-semibold uppercase tracking-[0.18em] ${sombre ? 'text-marine-200' : 'text-ardoise-400'}`}>
          Juridique · Comptable · Social
        </span>
      </span>
    </Link>
  )
}
