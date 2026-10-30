import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import * as api from '../data/api.js'

const ContexteSession = createContext(null)

export function FournisseurSession({ children }) {
  const [etat, setEtat] = useState({ chargement: true, client: null })

  useEffect(() => {
    let actif = true
    api.getSession().then((client) => actif && setEtat({ chargement: false, client }))
    return () => {
      actif = false
    }
  }, [])

  const connecter = useCallback(async (email, motDePasse) => {
    const client = await api.login(email, motDePasse)
    setEtat({ chargement: false, client })
  }, [])

  const deconnecter = useCallback(async () => {
    await api.logout()
    setEtat({ chargement: false, client: null })
  }, [])

  return <ContexteSession.Provider value={{ ...etat, connecter, deconnecter }}>{children}</ContexteSession.Provider>
}

export const useSession = () => useContext(ContexteSession)

// Garde de route : renvoie vers la connexion en mémorisant la page demandée.
export function RouteProtegee({ children }) {
  const { chargement, client } = useSession()
  const location = useLocation()
  if (chargement) return null
  if (!client) return <Navigate to="/espace-client/connexion" replace state={{ depuis: location.pathname }} />
  return children
}
