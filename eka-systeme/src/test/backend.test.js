import { creerServeur } from '../../server/serveur.js'
import { creerAdaptateur } from '../data/api.js'
import { creerAdaptateurHttp } from '../data/adaptateurs/http.js'
import { creerAdaptateurMock } from '../data/adaptateurs/mock.js'

const EMAIL = 'k.berrada@atlas-negoce.ma'
let serveur, baseUrl

beforeAll(async () => {
  serveur = creerServeur()
  await new Promise((ok) => serveur.listen(0, '127.0.0.1', ok))
  baseUrl = `http://127.0.0.1:${serveur.address().port}/api`
})
afterAll(() => new Promise((ok) => serveur.close(ok)))
beforeEach(() => window.sessionStorage.clear())

describe('choix de l’adaptateur', () => {
  it('prend mock par défaut et refuse une valeur inconnue', () => {
    expect(creerAdaptateur({})).toHaveProperty('getDossiers')
    expect(creerAdaptateur({ VITE_EKA_API: 'http', VITE_EKA_API_URL: baseUrl })).toHaveProperty('getDossiers')
    expect(() => creerAdaptateur({ VITE_EKA_API: 'supabase' })).toThrow(/inconnu/)
  })
})

describe('adaptateur http + serveur de démonstration', () => {
  it('protège les données derrière la connexion', async () => {
    const api = creerAdaptateurHttp({ baseUrl })
    expect(await api.getSession()).toBeNull()
    await expect(api.getDossiers()).rejects.toMatchObject({ statut: 401 })
    await expect(api.login(EMAIL, 'faux')).rejects.toThrow('Identifiants incorrects.')

    const client = await api.login(' K.Berrada@atlas-negoce.ma', 'demo2026')
    expect(client.raisonSociale).toBe('ATLAS NÉGOCE SARL')
    expect((await api.getSession()).utilisateur.prenom).toBe('Karim')

    await api.logout()
    expect(await api.getSession()).toBeNull()
  })

  it('renvoie un jeton invalide vers la déconnexion', async () => {
    const api = creerAdaptateurHttp({ baseUrl })
    await api.login(EMAIL, 'demo2026')
    window.sessionStorage.setItem('eka-jeton', 'perime')
    await expect(api.getEcheances()).rejects.toMatchObject({ statut: 401 })
    expect(window.sessionStorage.getItem('eka-jeton')).toBeNull()
  })

  it('sert exactement les mêmes données que l’adaptateur mock', async () => {
    const http = creerAdaptateurHttp({ baseUrl })
    const memoire = creerAdaptateurMock()
    await http.login(EMAIL, 'demo2026')
    for (const methode of ['getDossiers', 'getEcheances', 'getPaie', 'getDocuments', 'getActivite']) {
      expect(await http[methode]()).toEqual(await memoire[methode]())
    }
    expect(await http.getDossier('JUR-CESSION')).toEqual(await memoire.getDossier('JUR-CESSION'))
    expect(await http.getDossier('ABSENT')).toBeNull()
  })

  it('signale un serveur injoignable', async () => {
    const api = creerAdaptateurHttp({ baseUrl: 'http://127.0.0.1:1/api' })
    window.sessionStorage.setItem('eka-jeton', 'x')
    await expect(api.getDossiers()).rejects.toMatchObject({ statut: 0, message: 'Serveur injoignable.' })
  })
})
