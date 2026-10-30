// Validation du formulaire de contact : renvoie la liste des champs manquants.
export function champsManquants({ nom = '', email = '', telephone = '', besoin = '', consentement = false }) {
  const manques = []
  if (nom.trim().length < 2) manques.push('votre nom complet')
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) manques.push('une adresse e-mail valide')
  if (!/^\+?\d{8,15}$/.test(telephone.replace(/[\s.()-]/g, ''))) manques.push('un numéro de téléphone valide')
  if (!besoin) manques.push('le domaine concerné')
  if (!consentement) manques.push('votre accord pour le traitement de la demande')
  return manques
}
