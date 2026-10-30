import { Link, Route, Routes } from 'react-router-dom'
import Connexion from './espace-client/Connexion.jsx'
import Dossier from './espace-client/Dossier.jsx'
import Dossiers from './espace-client/Dossiers.jsx'
import Documents from './espace-client/Documents.jsx'
import Echeancier from './espace-client/Echeancier.jsx'
import Gabarit from './espace-client/Gabarit.jsx'
import Paie from './espace-client/Paie.jsx'
import TableauDeBord from './espace-client/TableauDeBord.jsx'
import { FournisseurSession, RouteProtegee } from './espace-client/session.jsx'
import Vitrine from './vitrine/Vitrine.jsx'

function PageIntrouvable() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-ardoise-50 px-6 text-center">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-or-600">Erreur 404</p>
      <h1 className="text-3xl">Cette page n’existe pas.</h1>
      <div className="flex flex-wrap justify-center gap-3">
        <Link to="/" className="rounded-lg bg-marine-800 px-5 py-3 text-sm font-semibold text-white">Site EKA CONSEIL</Link>
        <Link to="/espace-client" className="rounded-lg px-5 py-3 text-sm font-semibold text-marine-800 ring-1 ring-inset ring-ardoise-200">Espace client</Link>
      </div>
    </main>
  )
}

export default function App() {
  return (
    <FournisseurSession>
      <Routes>
        <Route path="/" element={<Vitrine />} />
        <Route path="/espace-client/connexion" element={<Connexion />} />
        <Route path="/espace-client" element={<RouteProtegee><Gabarit /></RouteProtegee>}>
          <Route index element={<TableauDeBord />} />
          <Route path="dossiers" element={<Dossiers />} />
          <Route path="dossiers/:id" element={<Dossier />} />
          <Route path="echeancier" element={<Echeancier />} />
          <Route path="paie" element={<Paie />} />
          <Route path="documents" element={<Documents />} />
        </Route>
        <Route path="*" element={<PageIntrouvable />} />
      </Routes>
    </FournisseurSession>
  )
}
