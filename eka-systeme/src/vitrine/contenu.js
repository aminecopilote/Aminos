// Textes de la vitrine EKA CONSEIL.

export const coordonnees = {
  adresse: 'Angle Bd Zerktouni & Rue Ibnou Mounir',
  quartier: 'Maârif, 20330 Casablanca',
  telephone: '+212 5 22 00 00 00',
  email: 'contact@eka-conseil.ma',
  horaires: 'Lundi — Vendredi, 9h00 — 18h00',
  whatsapp: 'https://wa.me/212600000000',
}

export const ancres = [
  { id: 'services', libelle: 'Nos services' },
  { id: 'valeur-ajoutee', libelle: 'Notre valeur ajoutée' },
  { id: 'methode', libelle: 'Notre méthode' },
  { id: 'faq', libelle: 'Questions fréquentes' },
  { id: 'contact', libelle: 'Contact' },
]

export const indicateurs = [
  ['12 ans', 'd’expérience cumulée'],
  ['250+', 'TPE & PME accompagnées'],
  ['48 h', 'de délai de traitement moyen'],
  ['100 %', 'des échéances fiscales tenues'],
]

export const apercuDossiers = [
  ['Déclaration TVA — Octobre', 'Transmise DGI', 'bon'],
  ['Paie — 14 bulletins', 'À valider', 'or'],
  ['PV d’assemblée annuelle', 'En rédaction', 'marine'],
  ['Dépôt de marque OMPIC', 'Enregistrée', 'bon'],
]

export const services = [
  {
    icone: 'building', titre: 'Création d’entreprises',
    accroche: 'Votre société constituée dans les règles, sans aller-retour inutile.',
    texte: 'Nous prenons en charge la constitution de votre société au Maroc de A à Z : choix de la forme juridique, formalités et immatriculation. Vous signez, nous gérons les administrations.',
    points: ['Conseil sur la forme juridique (SARL, SARL AU, SA, SNC)', 'Certificat négatif et réservation de dénomination (OMPIC)', 'Rédaction des statuts et actes de constitution', 'Immatriculation au registre du commerce, IF, TP et CNSS', 'Ouverture du compte bancaire et dépôt du capital'],
    delai: 'Société opérationnelle en 7 à 10 jours ouvrés',
  },
  {
    icone: 'calculator', titre: 'Comptabilité & Fiscalité', vedette: true,
    accroche: 'Une comptabilité tenue au PCGM et des déclarations toujours à l’heure.',
    texte: 'Tenue comptable rigoureuse, arrêtés périodiques et obligations fiscales maîtrisées. Nos outils génèrent automatiquement vos télédéclarations, dont les fichiers XML Simpl-TVA destinés à la DGI.',
    points: ['Tenue comptable complète selon le PCGM', 'Établissement des états de synthèse et de la liasse fiscale', 'Télédéclarations IS, IR et TVA (génération XML Simpl-TVA DGI)', 'Suivi de trésorerie et reporting de gestion mensuel', 'Assistance en cas de contrôle fiscal'],
    delai: 'Reporting de gestion transmis avant le 10 du mois',
  },
  {
    icone: 'users', titre: 'Gestion de la Paie & RH',
    accroche: 'Votre paie externalisée, vos déclarations sociales sécurisées.',
    texte: 'Nous prenons en charge l’intégralité du cycle de paie et l’administration du personnel : des bulletins conformes, des déclarations CNSS et AMO dans les délais, des dossiers salariés tenus à jour.',
    points: ['Externalisation complète du cycle de paie', 'Édition des bulletins de salaire et ordres de virement', 'Déclarations sociales CNSS, AMO et retraite complémentaire', 'Rédaction des contrats de travail, avenants et attestations', 'Suivi des congés, absences, soldes et fins de contrat'],
    delai: 'Bulletins validés 5 jours avant la date de paiement',
  },
  {
    icone: 'shield', titre: 'Protection & Enregistrement des marques',
    accroche: 'Votre marque déposée, surveillée et défendue auprès de l’OMPIC.',
    texte: 'Nous sécurisons votre actif immatériel le plus exposé : recherche d’antériorité, dépôt dans les classes utiles, puis surveillance et renouvellement de vos droits sur la durée.',
    points: ['Recherche d’antériorité et étude de disponibilité', 'Stratégie de classes (classification de Nice) et périmètre de dépôt', 'Dépôt et suivi de la procédure auprès de l’OMPIC', 'Réponse aux oppositions et objections de l’Office', 'Surveillance, renouvellement et extension à l’international'],
    delai: 'Dossier déposé sous 48 h après validation',
  },
  {
    icone: 'scale', titre: 'Suivi Juridique',
    accroche: 'Un secrétariat juridique courant et exceptionnel assuré en continu.',
    texte: 'Votre vie sociale documentée et conforme, année après année : assemblées, actes, modifications statutaires et opérations sur le capital, rédigés et déposés par nos juristes.',
    points: ['Secrétariat juridique annuel (convocations, PV d’AG, rapports)', 'Cessions de parts sociales et entrées d’associés', 'Modifications statutaires : objet, siège, capital, gérance', 'Rédaction et revue des contrats commerciaux', 'Dissolution, liquidation et opérations exceptionnelles'],
    delai: 'Projet d’acte transmis sous 72 h',
  },
]

export const atouts = [
  { icone: 'eye', titre: 'Suivi transparent de vos dossiers', texte: 'Chaque dossier juridique, comptable ou social dispose d’une fiche d’avancement en ligne : étape en cours, pièce attendue, interlocuteur responsable, échéance.' },
  { icone: 'bolt', titre: 'Déclarations générées automatiquement', texte: 'Nos interfaces produisent vos liasses, bulletins de paie et fichiers XML Simpl-TVA directement depuis vos écritures. Moins de ressaisie, donc moins d’erreurs.' },
  { icone: 'cloud', titre: 'Coffre-fort documentaire centralisé', texte: 'Statuts, PV, contrats de travail, bulletins et déclarations archivés au même endroit, horodatés et accessibles à vos équipes autorisées.' },
  { icone: 'clock', titre: 'Échéancier et alertes réglementaires', texte: 'Vos obligations fiscales et sociales sont calendées. Vous recevez l’alerte avant l’échéance, pas la pénalité après.' },
]

export const chiffresPlateforme = [
  ['-70 %', 'de ressaisie sur les déclarations'],
  ['24/7', 'd’accès à vos documents'],
  ['0', 'échéance oubliée depuis 2019'],
]

export const etapesMethode = [
  ['Diagnostic', 'Un premier entretien de 45 minutes pour cadrer votre situation, vos obligations réelles et vos risques immédiats.'],
  ['Proposition chiffrée', 'Une lettre de mission claire : périmètre, livrables, calendrier et honoraires fixes. Pas de facturation à la surprise.'],
  ['Mise en place', 'Reprise de vos dossiers, régularisation des retards éventuels et ouverture de vos accès à EKA SYSTÈME.'],
  ['Pilotage continu', 'Production des échéances, reporting mensuel et point de revue trimestriel avec votre interlocuteur dédié.'],
]

export const faq = [
  ['Travaillez-vous avec des entreprises déjà constituées ?', 'Oui. La reprise de dossier représente une grande part de nos missions. Nous réalisons un audit de conformité, régularisons les retards comptables, fiscaux et sociaux, puis reprenons le pilotage courant.'],
  ['Quels documents dois-je fournir pour créer ma société ?', 'Pour une SARL ou SARL AU : la pièce d’identité de chaque associé, l’adresse du siège (contrat de bail, domiciliation ou attestation), la répartition du capital et trois propositions de dénomination. Nous nous chargeons du reste des formalités.'],
  ['Comment se déroule la bascule de la paie vers votre cabinet ?', 'Nous reprenons l’historique de l’exercice en cours, les contrats et les cumuls CNSS, puis nous produisons un mois en double pour contrôle avant la bascule définitive. La continuité de vos déclarations est garantie.'],
  ['Vos honoraires sont-ils forfaitaires ?', 'Les missions récurrentes — comptabilité, paie, secrétariat juridique — sont facturées au forfait mensuel ou annuel, défini dans la lettre de mission. Les opérations exceptionnelles font l’objet d’un devis distinct avant engagement.'],
  ['Mes données sont-elles protégées sur EKA SYSTÈME ?', 'Les accès sont nominatifs et tracés, les échanges chiffrés et les données hébergées sur une infrastructure dédiée. Nos traitements respectent la loi 09-08 relative à la protection des données personnelles.'],
]

export const besoins = [
  ['creation', 'Création d’entreprise'],
  ['comptabilite', 'Comptabilité & Fiscalité'],
  ['paie', 'Gestion de Paie & RH'],
  ['juridique', 'Suivi Juridique'],
  ['marques', 'Dépôt de Marque'],
  ['autre', 'Autre demande'],
]
