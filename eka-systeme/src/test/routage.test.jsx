import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../App.jsx'

const rendre = (chemin) =>
  render(
    <MemoryRouter initialEntries={[chemin]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>,
  )

// Ouvre une session de démonstration avant de visiter l'espace client.
const connecte = () => window.sessionStorage.setItem('eka-session', 'demo')

beforeEach(() => window.sessionStorage.clear())

describe('vitrine', () => {
  it('affiche le cabinet et un lien vers l’espace client', async () => {
    rendre('/')
    expect(await screen.findByRole('heading', { level: 1, name: /Votre entreprise accompagnée/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Cinq expertises, un seul cabinet responsable de vos obligations.' })).toBeInTheDocument()
    const liens = screen.getAllByRole('link', { name: 'Espace client' })
    expect(liens[0]).toHaveAttribute('href', '/espace-client')
  })

  it('refuse un formulaire incomplet puis accepte un formulaire valide', async () => {
    const u = userEvent.setup()
    rendre('/')
    const form = await screen.findByRole('form', { name: 'Demande de consultation' })
    await u.click(within(form).getByRole('button', { name: /Demander ma consultation/ }))
    expect(within(form).getByRole('alert')).toHaveTextContent('votre nom complet')

    await u.type(within(form).getByLabelText(/Nom et prénom/), 'Yassine El Amrani')
    await u.type(within(form).getByLabelText(/Adresse e-mail/), 'y.elamrani@exemple.ma')
    await u.type(within(form).getByLabelText(/Téléphone/), '06 12 34 56 78')
    await u.selectOptions(within(form).getByLabelText(/Votre besoin/), 'paie')
    await u.click(within(form).getByLabelText(/J’autorise/))
    await u.click(within(form).getByRole('button', { name: /Demander ma consultation/ }))
    expect(within(form).getByRole('status')).toHaveTextContent('Demande enregistrée')
  })
})

describe('espace client', () => {
  it('redirige vers la connexion sans session, puis vers la page demandée', async () => {
    const u = userEvent.setup()
    rendre('/espace-client/paie')
    expect(await screen.findByRole('heading', { name: 'Connexion à votre espace' })).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Paie & RH' })).toBeInTheDocument()
  })

  it('refuse des identifiants incorrects', async () => {
    const u = userEvent.setup()
    rendre('/espace-client/connexion')
    const mdp = await screen.findByLabelText('Mot de passe')
    await u.clear(mdp)
    await u.type(mdp, 'faux')
    await u.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Identifiants incorrects')
  })

  it('navigue entre les rubriques et ouvre un dossier', async () => {
    connecte()
    const u = userEvent.setup()
    rendre('/espace-client')
    expect(await screen.findByRole('heading', { level: 1, name: 'Bonjour Karim' })).toBeInTheDocument()

    const nav = screen.getByRole('navigation', { name: 'Navigation de l’espace client' })
    await u.click(within(nav).getByRole('link', { name: /Échéancier/ }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Échéancier réglementaire' })).toBeInTheDocument()

    await u.click(within(nav).getByRole('link', { name: /Coffre-fort/ }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Coffre-fort documentaire' })).toBeInTheDocument()

    await u.click(within(nav).getByRole('link', { name: /Mes dossiers/ }))
    await u.click(await screen.findByRole('link', { name: /Cession de parts/ }))
    expect(await screen.findByRole('heading', { level: 1, name: /Cession de parts/ })).toBeInTheDocument()
    expect(screen.getByText('2 pièce(s) attendue(s) de votre part')).toBeInTheDocument()
  })

  it('signale un dossier inconnu', async () => {
    connecte()
    rendre('/espace-client/dossiers/INCONNU')
    expect(await screen.findByRole('heading', { name: 'Dossier introuvable' })).toBeInTheDocument()
  })

  it('ramène au site vitrine à la déconnexion puis depuis la connexion', async () => {
    connecte()
    const u = userEvent.setup()
    rendre('/espace-client')
    await u.click(await screen.findByRole('button', { name: 'Se déconnecter' }))
    expect(await screen.findByRole('heading', { name: 'Connexion à votre espace' })).toBeInTheDocument()
    await u.click(screen.getByRole('link', { name: /Retour au site EKA CONSEIL/ }))
    expect(screen.getByRole('heading', { level: 1, name: /Votre entreprise accompagnée/ })).toBeInTheDocument()
  })
})

it('affiche une page 404 pour une route inconnue', async () => {
  rendre('/nulle-part')
  expect(await screen.findByRole('heading', { name: 'Cette page n’existe pas.' })).toBeInTheDocument()
})
