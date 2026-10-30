// Données de démonstration du client ATLAS NÉGOCE SARL.
// Les écrans ne lisent jamais ce fichier directement : ils passent par api.js.

export const client = {
  raisonSociale: 'ATLAS NÉGOCE SARL',
  identifiants: 'IF 40512876 · RC Casablanca 458721 · Exercice 2026',
  utilisateur: { prenom: 'Karim', nom: 'Berrada', initiales: 'KB', fonction: 'Gérant', email: 'k.berrada@atlas-negoce.ma' },
  interlocuteur: { nom: 'Nadia Benali', fonction: 'Responsable de mission', email: 'n.benali@eka-conseil.ma' },
  notificationsNonLues: 3,
}

export const dossiers = [
  {
    id: 'TVA-2610', intitule: 'Télédéclaration TVA — octobre 2026', pole: 'comptabilite', etat: 'enCours', avancement: 60, echeance: '2026-11-20', responsable: 'Nadia Benali', majLe: '2026-10-16',
    etapes: [
      { titre: 'Collecte des pièces comptables', etat: 'termine', date: '2026-10-05' },
      { titre: 'Saisie et lettrage des écritures', etat: 'termine', date: '2026-10-12' },
      { titre: 'Contrôle de cohérence TVA déductible', etat: 'enCours', date: '2026-10-16' },
      { titre: 'Génération du fichier XML Simpl-TVA', etat: 'aVenir', date: '2026-11-17' },
      { titre: 'Télétransmission DGI et accusé de dépôt', etat: 'aVenir', date: '2026-11-20' },
    ],
    pieces: [
      { intitule: 'Relevés bancaires — octobre', etat: 'recu' },
      { intitule: 'Factures d’achat — octobre', etat: 'recu' },
      { intitule: 'Factures de vente — 2e quinzaine', etat: 'attendu' },
    ],
  },
  {
    id: 'PAIE-2610', intitule: 'Paie octobre — 14 bulletins', pole: 'paie', etat: 'aValider', avancement: 85, echeance: '2026-10-27', responsable: 'Youssef Lahlou', majLe: '2026-10-17',
    etapes: [
      { titre: 'Réception des variables (absences, primes)', etat: 'termine', date: '2026-10-10' },
      { titre: 'Calcul des bulletins et des cotisations', etat: 'termine', date: '2026-10-15' },
      { titre: 'Validation du gérant', etat: 'enCours', date: '2026-10-17' },
      { titre: 'Édition des bulletins et ordre de virement', etat: 'aVenir', date: '2026-10-27' },
      { titre: 'Télédéclaration CNSS (DAMANCOM)', etat: 'aVenir', date: '2026-11-30' },
    ],
    pieces: [
      { intitule: 'État des absences — octobre', etat: 'recu' },
      { intitule: 'Décision de prime exceptionnelle', etat: 'recu' },
    ],
  },
  {
    id: 'JUR-AGO25', intitule: 'Assemblée générale ordinaire — exercice 2025', pole: 'juridique', etat: 'enCours', avancement: 40, echeance: '2026-11-30', responsable: 'Salma Chraïbi', majLe: '2026-10-14',
    etapes: [
      { titre: 'Rapport de gestion du gérant', etat: 'termine', date: '2026-10-08' },
      { titre: 'Rédaction du procès-verbal d’AGO', etat: 'enCours', date: '2026-10-14' },
      { titre: 'Signature des associés', etat: 'aVenir', date: '2026-11-20' },
      { titre: 'Dépôt au greffe du tribunal de commerce', etat: 'aVenir', date: '2026-11-30' },
    ],
    pieces: [{ intitule: 'États de synthèse 2025 approuvés', etat: 'recu' }],
  },
  {
    id: 'MQ-ATLASFRESH', intitule: 'Dépôt de marque « ATLAS FRESH » — classes 29, 31, 35', pole: 'marques', etat: 'termine', avancement: 100, echeance: '2026-09-18', responsable: 'Salma Chraïbi', majLe: '2026-09-18',
    etapes: [
      { titre: 'Recherche d’antériorité', etat: 'termine', date: '2026-07-02' },
      { titre: 'Dépôt auprès de l’OMPIC', etat: 'termine', date: '2026-07-11' },
      { titre: 'Publication au catalogue officiel', etat: 'termine', date: '2026-08-20' },
      { titre: 'Certificat d’enregistrement délivré', etat: 'termine', date: '2026-09-18' },
    ],
    pieces: [{ intitule: 'Certificat d’enregistrement OMPIC', etat: 'recu' }],
  },
  {
    id: 'JUR-CESSION', intitule: 'Cession de parts — M. Berrada vers Mme Idrissi', pole: 'juridique', etat: 'attentePieces', avancement: 25, echeance: '2026-12-15', responsable: 'Salma Chraïbi', majLe: '2026-10-09',
    etapes: [
      { titre: 'Projet d’acte de cession', etat: 'termine', date: '2026-10-09' },
      { titre: 'Pièces d’identité du cessionnaire', etat: 'enCours', date: '2026-10-09' },
      { titre: 'PV d’assemblée autorisant la cession', etat: 'aVenir', date: '2026-11-25' },
      { titre: 'Enregistrement et dépôt modificatif', etat: 'aVenir', date: '2026-12-15' },
    ],
    pieces: [
      { intitule: 'CIN de Mme Idrissi', etat: 'attendu' },
      { intitule: 'Attestation de domicile du cessionnaire', etat: 'attendu' },
    ],
  },
  {
    id: 'LIASSE-2025', intitule: 'Liasse fiscale — exercice 2025', pole: 'comptabilite', etat: 'termine', avancement: 100, echeance: '2026-03-31', responsable: 'Nadia Benali', majLe: '2026-03-28',
    etapes: [
      { titre: 'Arrêté des comptes et états de synthèse', etat: 'termine', date: '2026-02-20' },
      { titre: 'Établissement de la liasse fiscale', etat: 'termine', date: '2026-03-10' },
      { titre: 'Télédéclaration IS et dépôt', etat: 'termine', date: '2026-03-28' },
    ],
    pieces: [{ intitule: 'Accusé de dépôt DGI', etat: 'recu' }],
  },
]

export const echeances = [
  { id: 'e1', intitule: 'Retenue à la source IR sur salaires — septembre', administration: 'DGI', date: '2026-10-31', montant: 24180, etat: 'aVenir' },
  { id: 'e2', intitule: 'Déclaration et paiement TVA — octobre', administration: 'DGI — Simpl-TVA', date: '2026-11-20', montant: 61450, etat: 'aVenir' },
  { id: 'e3', intitule: 'Télédéclaration CNSS et AMO — octobre', administration: 'CNSS — DAMANCOM', date: '2026-11-30', montant: 38920, etat: 'aVenir' },
  { id: 'e4', intitule: '4e acompte provisionnel IS — exercice 2026', administration: 'DGI', date: '2026-12-31', montant: 52000, etat: 'aVenir' },
  { id: 'e5', intitule: 'Dépôt du PV d’assemblée générale ordinaire 2025', administration: 'Tribunal de commerce', date: '2026-11-30', montant: null, etat: 'urgente' },
  { id: 'e6', intitule: 'Déclaration et paiement TVA — septembre', administration: 'DGI — Simpl-TVA', date: '2026-10-20', montant: 57310, etat: 'tenue' },
  { id: 'e7', intitule: 'Télédéclaration CNSS et AMO — septembre', administration: 'CNSS — DAMANCOM', date: '2026-10-31', montant: 37650, etat: 'tenue' },
]

export const paie = {
  periode: 'Octobre 2026',
  masseSalariale: [
    { mois: 'Mai', brut: 171200 }, { mois: 'Juin', brut: 174900 }, { mois: 'Juil.', brut: 178600 },
    { mois: 'Août', brut: 169400 }, { mois: 'Sept.', brut: 181000 }, { mois: 'Oct.', brut: 186400 },
  ],
  synthese: { brut: 186400, cotisationsSalariales: 12142, cotisationsPatronales: 38920, irRetenu: 24180, net: 150078, bulletins: 14, effectif: 14 },
  salaries: [
    { matricule: 'S-001', nom: 'Karim Berrada', poste: 'Gérant', contrat: 'CDI', brut: 32000, net: 24380 },
    { matricule: 'S-002', nom: 'Fatima Zahra Ouali', poste: 'Responsable administrative', contrat: 'CDI', brut: 18500, net: 14920 },
    { matricule: 'S-003', nom: 'Mehdi Tazi', poste: 'Responsable logistique', contrat: 'CDI', brut: 16800, net: 13640 },
    { matricule: 'S-004', nom: 'Imane Sefrioui', poste: 'Comptable interne', contrat: 'CDI', brut: 14200, net: 11680 },
    { matricule: 'S-005', nom: 'Hamza El Fassi', poste: 'Commercial terrain', contrat: 'CDI', brut: 12600, net: 10490 },
    { matricule: 'S-006', nom: 'Khadija Amrani', poste: 'Assistante commerciale', contrat: 'CDD', brut: 9400, net: 8010 },
    { matricule: 'S-007', nom: 'Omar Bennis', poste: 'Magasinier', contrat: 'CDI', brut: 7200, net: 6230 },
    { matricule: 'S-008', nom: 'Rachid Alaoui', poste: 'Chauffeur-livreur', contrat: 'CDI', brut: 6800, net: 5910 },
  ],
}

export const documents = {
  categories: [
    { libelle: 'Juridique', total: 23 }, { libelle: 'Comptable', total: 148 }, { libelle: 'Fiscal', total: 41 },
    { libelle: 'Paie & RH', total: 96 }, { libelle: 'Marques', total: 7 },
  ],
  recents: [
    { id: 'd1', nom: 'Certificat d’enregistrement OMPIC — ATLAS FRESH.pdf', categorie: 'Marques', poids: '412 Ko', depose: '2026-09-18' },
    { id: 'd2', nom: 'Accusé de dépôt TVA — septembre 2026.pdf', categorie: 'Fiscal', poids: '168 Ko', depose: '2026-10-20' },
    { id: 'd3', nom: 'Bulletins de paie — septembre 2026.zip', categorie: 'Paie & RH', poids: '2,4 Mo', depose: '2026-09-27' },
    { id: 'd4', nom: 'Bordereau CNSS — septembre 2026.pdf', categorie: 'Paie & RH', poids: '94 Ko', depose: '2026-10-31' },
    { id: 'd5', nom: 'Contrat de travail CDI — M. Tazi.pdf', categorie: 'Juridique', poids: '220 Ko', depose: '2026-08-04' },
    { id: 'd6', nom: 'États de synthèse — exercice 2025.pdf', categorie: 'Comptable', poids: '1,1 Mo', depose: '2026-03-28' },
  ],
}

export const activite = [
  { date: '2026-10-17', texte: 'Bulletins de paie d’octobre soumis à votre validation.', par: 'Youssef Lahlou' },
  { date: '2026-10-16', texte: 'Contrôle de cohérence de la TVA déductible d’octobre engagé.', par: 'Nadia Benali' },
  { date: '2026-10-14', texte: 'Projet de procès-verbal d’assemblée générale 2025 déposé.', par: 'Salma Chraïbi' },
  { date: '2026-10-09', texte: 'Deux pièces manquantes relancées sur la cession de parts.', par: 'Salma Chraïbi' },
]

// Identifiants de démonstration acceptés par la connexion simulée.
export const COMPTE_DEMO = { email: 'k.berrada@atlas-negoce.ma', motDePasse: 'demo2026' }
