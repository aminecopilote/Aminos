// Bibliothèque d'icônes au trait, reprise de la maquette.
const TRACES = {
  building: <><path d="M3 21h18" /><path d="M5 21V6a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v15" /><path d="M14 21V10h4a1 1 0 0 1 1 1v10" /><path d="M8 8h3M8 11.5h3M8 15h3" /></>,
  calculator: <><rect x="4" y="3" width="16" height="18" rx="2" /><rect x="7.5" y="6" width="9" height="3.5" rx="1" /><path d="M8.5 13h.01M12 13h.01M15.5 13h.01M8.5 16.5h.01M12 16.5h.01M15.5 16.5h.01" /></>,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><circle cx="17.5" cy="9.5" r="2.5" /><path d="M17 14.5c2.5 0 4.5 2 4.5 4.5" /></>,
  shield: <><path d="M12 3 5 5.6v5.3c0 4.2 2.8 8.1 7 9.1 4.2-1 7-4.9 7-9.1V5.6L12 3Z" /><path d="m9 11.8 2.2 2.2L15.5 9.7" /></>,
  scale: <><path d="M12 3.5v2" /><path d="M4.5 6.5h15" /><path d="M8 21h8" /><path d="M12 6.5V21" /><path d="M4.5 6.5 2 13a3.5 3.5 0 0 0 5 0L4.5 6.5Z" /><path d="M19.5 6.5 17 13a3.5 3.5 0 0 0 5 0L19.5 6.5Z" /></>,
  bolt: <path d="M13 3 5 13.5h5l-1 7.5 8-10.5h-5l1-7.5Z" />,
  eye: <><path d="M2.5 12S6 6.5 12 6.5 21.5 12 21.5 12 18 17.5 12 17.5 2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="3" /></>,
  cloud: <path d="M7 18h10a4 4 0 0 0 .5-8 6 6 0 0 0-11.6 1.6A3.5 3.5 0 0 0 6.5 18H7Z" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7.5V12l3.5 2" /></>,
  check: <path d="m5 12.5 4.5 4.5L19 7" />,
  arrow: <><path d="M4 12h15" /><path d="m13 6 6 6-6 6" /></>,
  phone: <path d="M15.5 21C8.6 21 3 15.4 3 8.5V7a2 2 0 0 1 2-2h2.2a1 1 0 0 1 1 .8l.7 3a1 1 0 0 1-.5 1.1l-1.4.7a10.6 10.6 0 0 0 4.9 4.9l.7-1.4a1 1 0 0 1 1.1-.5l3 .7a1 1 0 0 1 .8 1V19a2 2 0 0 1-2 2h-.5Z" />,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3.5 7 8.5 6 8.5-6" /></>,
  pin: <><path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></>,
  whatsapp: <><path d="M20.5 11.8a8.5 8.5 0 0 1-12.6 7.4L3.5 20.5l1.4-4.2A8.5 8.5 0 1 1 20.5 11.8Z" /><path d="M9.2 8.4c0 3.1 2.5 5.6 5.6 5.6.5 0 .9-.4.9-.9v-.7l-1.8-.7-.8.9a5.3 5.3 0 0 1-2.2-2.2l.9-.8-.7-1.8h-.9c-.5 0-.9.4-.9.9Z" /></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  chevron: <path d="m6 9.5 6 6 6-6" />,
  cpu: <><rect x="6" y="6" width="12" height="12" rx="2" /><rect x="9.5" y="9.5" width="5" height="5" rx="1" /><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3" /></>,
  document: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" /><path d="M14 3v5h5" /><path d="M9 13h6M9 16.5h4" /></>,
  bell: <><path d="M18 9a6 6 0 1 0-12 0c0 4-1.5 5-2 6h16c-.5-1-2-2-2-6Z" /><path d="M10 19a2 2 0 0 0 4 0" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  logout: <><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /><path d="M10 16l-4-4 4-4" /><path d="M6 12h10" /></>,
}

export default function Icone({ nom, className = '', trait }) {
  return (
    <svg viewBox="0 0 24 24" className={`ico ${className}`} style={trait ? { strokeWidth: trait } : undefined} aria-hidden="true">
      {TRACES[nom]}
    </svg>
  )
}
