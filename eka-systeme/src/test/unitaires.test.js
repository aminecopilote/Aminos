import { dateCourte, joursRestants, mad } from '../data/format.js'
import { champsManquants } from '../vitrine/validation.js'
import * as api from '../data/api.js'

describe('format', () => {
  it('formate montants et dates à la française', () => {
    expect(mad(61450).replace(/\s/g, ' ')).toBe('61 450 MAD')
    expect(mad(null)).toBe('—')
    expect(dateCourte('2026-11-20')).toBe('20/11/2026')
    expect(joursRestants('2026-10-31')).toBe(14)
  })
})

describe('validation du contact', () => {
  it('liste chaque champ manquant', () => {
    expect(champsManquants({})).toHaveLength(5)
    expect(champsManquants({ nom: 'Yassine', email: 'y@ex.ma', telephone: '+212 6 12 34 56 78', besoin: 'paie', consentement: true })).toEqual([])
  })
})

describe('api simulée', () => {
  beforeEach(() => window.sessionStorage.clear())

  it('ne renvoie pas de session avant connexion', async () => {
    expect(await api.getSession()).toBeNull()
    await expect(api.login('x@y.ma', 'nope')).rejects.toThrow()
    const client = await api.login('K.Berrada@atlas-negoce.ma ', 'demo2026')
    expect(client.raisonSociale).toBe('ATLAS NÉGOCE SARL')
    await api.logout()
    expect(await api.getSession()).toBeNull()
  })

  it('renvoie des copies, pas les objets du mock', async () => {
    const a = await api.getDossier('TVA-2610')
    a.intitule = 'modifié'
    expect((await api.getDossier('TVA-2610')).intitule).not.toBe('modifié')
    expect(await api.getDossier('ABSENT')).toBeNull()
  })
})
