// Contrat de données de l'espace client, partagé par tous les adaptateurs
// (mock en mémoire, HTTP vers le serveur d'API, futur backend réel).
// Les formes suivent src/data/mock.js ; les dates sont des chaînes ISO « AAAA-MM-JJ ».

/**
 * @typedef {Object} Client
 * @property {string} raisonSociale
 * @property {string} identifiants
 * @property {{prenom: string, nom: string, initiales: string, fonction: string, email: string}} utilisateur
 * @property {{nom: string, fonction: string, email: string}} interlocuteur
 * @property {number} notificationsNonLues
 */

/**
 * @typedef {'termine'|'aValider'|'enCours'|'attentePieces'} EtatDossier
 * @typedef {{titre: string, etat: 'termine'|'enCours'|'aVenir', date: string}} Etape
 * @typedef {{intitule: string, etat: 'recu'|'attendu'}} Piece
 * @typedef {Object} Dossier
 * @property {string} id
 * @property {string} intitule
 * @property {'comptabilite'|'paie'|'juridique'|'marques'} pole
 * @property {EtatDossier} etat
 * @property {number} avancement  Pourcentage de 0 à 100.
 * @property {string} echeance
 * @property {string} responsable
 * @property {string} majLe
 * @property {Etape[]} etapes
 * @property {Piece[]} pieces
 */

/**
 * @typedef {Object} Echeance
 * @property {string} id
 * @property {string} intitule
 * @property {string} administration
 * @property {string} date
 * @property {number|null} montant  En dirhams, null si sans paiement.
 * @property {'aVenir'|'urgente'|'tenue'} etat
 */

/**
 * @typedef {Object} Paie
 * @property {string} periode
 * @property {{mois: string, brut: number}[]} masseSalariale
 * @property {{brut: number, cotisationsSalariales: number, cotisationsPatronales: number, irRetenu: number, net: number, bulletins: number, effectif: number}} synthese
 * @property {{matricule: string, nom: string, poste: string, contrat: string, brut: number, net: number}[]} salaries
 */

/**
 * @typedef {Object} Documents
 * @property {{libelle: string, total: number}[]} categories
 * @property {{id: string, nom: string, categorie: string, poids: string, depose: string}[]} recents
 */

/** @typedef {{date: string, texte: string, par: string}} Activite */

/**
 * Interface que chaque adaptateur doit fournir.
 * @typedef {Object} Adaptateur
 * @property {(email: string, motDePasse: string) => Promise<Client>} login  Rejette une Error si refus.
 * @property {() => Promise<void>} logout
 * @property {() => Promise<Client|null>} getSession
 * @property {() => Promise<Dossier[]>} getDossiers
 * @property {(id: string) => Promise<Dossier|null>} getDossier
 * @property {() => Promise<Echeance[]>} getEcheances
 * @property {() => Promise<Paie>} getPaie
 * @property {() => Promise<Documents>} getDocuments
 * @property {() => Promise<Activite[]>} getActivite
 */

export {}
