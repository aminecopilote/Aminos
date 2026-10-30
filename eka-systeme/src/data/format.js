// Mise en forme française des montants et des dates.
export const AUJOURDHUI = new Date('2026-10-17T00:00:00')

const nf = new Intl.NumberFormat('fr-FR')

export const nombre = (v) => nf.format(v)
export const mad = (v) => (v == null ? '—' : `${nf.format(v)} MAD`)
export const dateCourte = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
export const joursRestants = (iso, depuis = AUJOURDHUI) =>
  Math.round((new Date(`${iso}T00:00:00`) - depuis) / 86400000)
