// Banque de questions et de défis (arabe + français).
// Question : { id, cat, level (1 facile, 2 moyen, 3 difficile), ar, fr, options: [[ar, fr] x4], answer: index }
// Défi : { id, ar, fr, points, seconds (0 = sans minuteur) }
(function (root) {
  "use strict";

  var categories = [
    { id: "general", icon: "💡", ar: "ثقافة عامة", fr: "Culture générale" },
    { id: "geo", icon: "🌍", ar: "جغرافيا", fr: "Géographie" },
    { id: "history", icon: "📜", ar: "تاريخ", fr: "Histoire" },
    { id: "science", icon: "🔬", ar: "علوم", fr: "Sciences" },
    { id: "sport", icon: "⚽", ar: "رياضة", fr: "Sport" },
    { id: "morocco", icon: "🕌", ar: "المغرب", fr: "Maroc" },
    { id: "riddles", icon: "🧩", ar: "ألغاز", fr: "Énigmes" }
  ];

  function Q(id, cat, level, ar, fr, options, answer) {
    return { id: id, cat: cat, level: level, ar: ar, fr: fr, options: options, answer: answer };
  }

  var questions = [
    // ثقافة عامة / Culture générale
    Q("g1", "general", 1, "كم عدد أيام السنة الكبيسة؟", "Combien de jours compte une année bissextile ?",
      [["365", "365"], ["366", "366"], ["364", "364"], ["367", "367"]], 1),
    Q("g2", "general", 1, "ما هو اللون الناتج عن مزج الأزرق والأصفر؟", "Quelle couleur obtient-on en mélangeant le bleu et le jaune ?",
      [["الأحمر", "Rouge"], ["البنفسجي", "Violet"], ["الأخضر", "Vert"], ["البرتقالي", "Orange"]], 2),
    Q("g3", "general", 2, "من رسم لوحة الموناليزا؟", "Qui a peint la Joconde ?",
      [["بيكاسو", "Picasso"], ["فان غوخ", "Van Gogh"], ["مايكل أنجلو", "Michel-Ange"], ["ليوناردو دا فينشي", "Léonard de Vinci"]], 3),
    Q("g4", "general", 1, "كم عدد أوتار الغيتار العادي؟", "Combien de cordes a une guitare classique ?",
      [["4", "4"], ["5", "5"], ["6", "6"], ["8", "8"]], 2),
    Q("g5", "general", 2, "ما هي عملة اليابان؟", "Quelle est la monnaie du Japon ?",
      [["الين", "Le yen"], ["اليوان", "Le yuan"], ["الوون", "Le won"], ["الروبية", "La roupie"]], 0),
    Q("g6", "general", 2, "ما هي اللغة الأكثر عددًا من المتحدثين الأصليين في العالم؟", "Quelle langue compte le plus de locuteurs natifs au monde ?",
      [["الإنجليزية", "L'anglais"], ["الصينية الماندرينية", "Le chinois mandarin"], ["الإسبانية", "L'espagnol"], ["العربية", "L'arabe"]], 1),
    Q("g7", "general", 1, "كم عدد ساعات اليوم؟", "Combien d'heures compte une journée ?",
      [["12", "12"], ["24", "24"], ["36", "36"], ["48", "48"]], 1),
    Q("g8", "general", 3, "كم عدد القطع على رقعة الشطرنج عند بداية المباراة؟", "Combien de pièces y a-t-il sur l'échiquier au début d'une partie ?",
      [["16", "16"], ["24", "24"], ["32", "32"], ["64", "64"]], 2),

    // جغرافيا / Géographie
    Q("geo1", "geo", 1, "ما هي عاصمة المغرب؟", "Quelle est la capitale du Maroc ?",
      [["الدار البيضاء", "Casablanca"], ["الرباط", "Rabat"], ["فاس", "Fès"], ["مراكش", "Marrakech"]], 1),
    Q("geo2", "geo", 1, "ما هو أطول نهر في إفريقيا؟", "Quel est le plus long fleuve d'Afrique ?",
      [["الكونغو", "Le Congo"], ["النيجر", "Le Niger"], ["النيل", "Le Nil"], ["الزمبيزي", "Le Zambèze"]], 2),
    Q("geo3", "geo", 2, "ما هي أكبر صحراء حارة في العالم؟", "Quel est le plus grand désert chaud du monde ?",
      [["الصحراء الكبرى", "Le Sahara"], ["صحراء غوبي", "Le désert de Gobi"], ["صحراء كالاهاري", "Le Kalahari"], ["صحراء أتاكاما", "L'Atacama"]], 0),
    Q("geo4", "geo", 1, "ما هو أكبر محيط في العالم؟", "Quel est le plus grand océan du monde ?",
      [["الأطلسي", "L'Atlantique"], ["الهندي", "L'Indien"], ["المتجمد الشمالي", "L'Arctique"], ["الهادئ", "Le Pacifique"]], 3),
    Q("geo5", "geo", 1, "ما هي أعلى قمة في العالم؟", "Quel est le plus haut sommet du monde ?",
      [["إيفرست", "L'Everest"], ["كليمنجارو", "Le Kilimandjaro"], ["مون بلان", "Le Mont-Blanc"], ["توبقال", "Le Toubkal"]], 0),
    Q("geo6", "geo", 2, "ما هي أعلى قمة في المغرب؟", "Quel est le plus haut sommet du Maroc ?",
      [["جبل العياشي", "Le jebel Ayachi"], ["جبل توبقال", "Le jebel Toubkal"], ["جبل مكون", "L'Ighil M'Goun"], ["جبل بويبلان", "Le Bou Iblane"]], 1),
    Q("geo7", "geo", 1, "ما اسم المضيق الذي يفصل المغرب عن إسبانيا؟", "Quel détroit sépare le Maroc de l'Espagne ?",
      [["مضيق البوسفور", "Le Bosphore"], ["مضيق هرمز", "Le détroit d'Ormuz"], ["مضيق جبل طارق", "Le détroit de Gibraltar"], ["مضيق باب المندب", "Le Bab-el-Mandeb"]], 2),
    Q("geo8", "geo", 3, "ما هي عاصمة كندا؟", "Quelle est la capitale du Canada ?",
      [["تورونتو", "Toronto"], ["مونتريال", "Montréal"], ["فانكوفر", "Vancouver"], ["أوتاوا", "Ottawa"]], 3),
    Q("geo9", "geo", 2, "ما هي أكبر دولة في العالم من حيث المساحة؟", "Quel est le plus grand pays du monde par sa superficie ?",
      [["الصين", "La Chine"], ["روسيا", "La Russie"], ["كندا", "Le Canada"], ["الولايات المتحدة", "Les États-Unis"]], 1),
    Q("geo10", "geo", 1, "ما هي عاصمة اليابان؟", "Quelle est la capitale du Japon ?",
      [["طوكيو", "Tokyo"], ["أوساكا", "Osaka"], ["كيوتو", "Kyoto"], ["سيول", "Séoul"]], 0),

    // تاريخ / Histoire
    Q("h1", "history", 2, "في أي سنة حصل المغرب على استقلاله؟", "En quelle année le Maroc a-t-il obtenu son indépendance ?",
      [["1912", "1912"], ["1944", "1944"], ["1956", "1956"], ["1962", "1962"]], 2),
    Q("h2", "history", 2, "في أي سنة نزل أول إنسان على سطح القمر؟", "En quelle année le premier homme a-t-il marché sur la Lune ?",
      [["1959", "1959"], ["1969", "1969"], ["1975", "1975"], ["1981", "1981"]], 1),
    Q("h3", "history", 1, "في أي بلد توجد أهرامات الجيزة؟", "Dans quel pays se trouvent les pyramides de Gizeh ?",
      [["مصر", "L'Égypte"], ["السودان", "Le Soudan"], ["العراق", "L'Irak"], ["المكسيك", "Le Mexique"]], 0),
    Q("h4", "history", 2, "في أي مدينة وُلد الرحالة ابن بطوطة؟", "Dans quelle ville est né le voyageur Ibn Battuta ?",
      [["فاس", "Fès"], ["طنجة", "Tanger"], ["سبتة", "Ceuta"], ["القاهرة", "Le Caire"]], 1),
    Q("h5", "history", 1, "في أي سنة انتهت الحرب العالمية الثانية؟", "En quelle année s'est terminée la Seconde Guerre mondiale ?",
      [["1918", "1918"], ["1939", "1939"], ["1945", "1945"], ["1950", "1950"]], 2),
    Q("h6", "history", 3, "في أي سنة ضرب الزلزال الكبير مدينة أكادير؟", "En quelle année le grand séisme a-t-il frappé Agadir ?",
      [["1955", "1955"], ["1960", "1960"], ["1969", "1969"], ["1980", "1980"]], 1),
    Q("h7", "history", 2, "في أي سنة نُظمت المسيرة الخضراء؟", "En quelle année a eu lieu la Marche verte ?",
      [["1956", "1956"], ["1970", "1970"], ["1975", "1975"], ["1984", "1984"]], 2),
    Q("h8", "history", 3, "من هي الدولة التي أسست مدينة مراكش؟", "Quelle dynastie a fondé la ville de Marrakech ?",
      [["المرابطون", "Les Almoravides"], ["الموحدون", "Les Almohades"], ["المرينيون", "Les Mérinides"], ["السعديون", "Les Saadiens"]], 0),
    Q("h9", "history", 2, "من اخترع المطبعة ذات الحروف المتحركة في أوروبا؟", "Qui a inventé l'imprimerie à caractères mobiles en Europe ?",
      [["غاليليو", "Galilée"], ["نيوتن", "Newton"], ["غوتنبرغ", "Gutenberg"], ["إديسون", "Edison"]], 2),

    // علوم / Sciences
    Q("s1", "science", 1, "ما هي الصيغة الكيميائية للماء؟", "Quelle est la formule chimique de l'eau ?",
      [["CO2", "CO2"], ["H2O", "H2O"], ["O2", "O2"], ["NaCl", "NaCl"]], 1),
    Q("s2", "science", 1, "عند أي درجة حرارة يغلي الماء على مستوى سطح البحر؟", "À quelle température l'eau bout-elle au niveau de la mer ?",
      [["50 درجة", "50 °C"], ["90 درجة", "90 °C"], ["100 درجة", "100 °C"], ["120 درجة", "120 °C"]], 2),
    Q("s3", "science", 1, "ما هو أقرب كوكب إلى الشمس؟", "Quelle est la planète la plus proche du Soleil ?",
      [["عطارد", "Mercure"], ["الزهرة", "Vénus"], ["المريخ", "Mars"], ["الأرض", "La Terre"]], 0),
    Q("s4", "science", 3, "كم عدد عظام جسم الإنسان البالغ؟", "Combien d'os compte le squelette d'un adulte ?",
      [["106", "106"], ["186", "186"], ["206", "206"], ["306", "306"]], 2),
    Q("s5", "science", 1, "ما هو الغاز الذي تمتصه النباتات من الهواء لصنع غذائها؟", "Quel gaz les plantes absorbent-elles pour fabriquer leur nourriture ?",
      [["الأكسجين", "L'oxygène"], ["ثاني أكسيد الكربون", "Le dioxyde de carbone"], ["الهيدروجين", "L'hydrogène"], ["الهيليوم", "L'hélium"]], 1),
    Q("s6", "science", 3, "ما هي سرعة الضوء تقريبًا؟", "Quelle est la vitesse approximative de la lumière ?",
      [["300 كلم في الثانية", "300 km/s"], ["3000 كلم في الثانية", "3 000 km/s"], ["300 ألف كلم في الثانية", "300 000 km/s"], ["3 ملايين كلم في الثانية", "3 millions de km/s"]], 2),
    Q("s7", "science", 2, "ما هو العنصر الذي رمزه الكيميائي Au؟", "Quel élément a pour symbole chimique Au ?",
      [["الفضة", "L'argent"], ["الألمنيوم", "L'aluminium"], ["النحاس", "Le cuivre"], ["الذهب", "L'or"]], 3),
    Q("s8", "science", 1, "ما هو العضو الذي يضخ الدم في الجسم؟", "Quel organe pompe le sang dans le corps ?",
      [["الكبد", "Le foie"], ["القلب", "Le cœur"], ["الرئتان", "Les poumons"], ["الكليتان", "Les reins"]], 1),
    Q("s9", "science", 1, "كم عدد أرجل العنكبوت؟", "Combien de pattes a une araignée ?",
      [["6", "6"], ["8", "8"], ["10", "10"], ["12", "12"]], 1),
    Q("s10", "science", 2, "ما هو أكبر كوكب في المجموعة الشمسية؟", "Quelle est la plus grande planète du système solaire ?",
      [["زحل", "Saturne"], ["المشتري", "Jupiter"], ["نبتون", "Neptune"], ["الأرض", "La Terre"]], 1),

    // رياضة / Sport
    Q("sp1", "sport", 1, "كم عدد لاعبي فريق كرة القدم داخل الملعب؟", "Combien de joueurs compte une équipe de football sur le terrain ?",
      [["9", "9"], ["10", "10"], ["11", "11"], ["12", "12"]], 2),
    Q("sp2", "sport", 2, "إلى أي دور وصل المنتخب المغربي في كأس العالم 2022؟", "Jusqu'à quel tour le Maroc est-il allé lors de la Coupe du monde 2022 ?",
      [["ربع النهائي", "Les quarts de finale"], ["نصف النهائي", "Les demi-finales"], ["النهائي", "La finale"], ["ثمن النهائي", "Les huitièmes de finale"]], 1),
    Q("sp3", "sport", 2, "مع أي بلدين ينظم المغرب كأس العالم 2030؟", "Avec quels pays le Maroc co-organise-t-il la Coupe du monde 2030 ?",
      [["فرنسا وإيطاليا", "La France et l'Italie"], ["إسبانيا والبرتغال", "L'Espagne et le Portugal"], ["الجزائر وتونس", "L'Algérie et la Tunisie"], ["مصر والسعودية", "L'Égypte et l'Arabie saoudite"]], 1),
    Q("sp4", "sport", 1, "كم عدد الحلقات في شعار الألعاب الأولمبية؟", "Combien d'anneaux compte le symbole olympique ?",
      [["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"]], 1),
    Q("sp5", "sport", 1, "في أي رياضة اشتهر هشام الكروج؟", "Dans quel sport Hicham El Guerrouj s'est-il illustré ?",
      [["كرة القدم", "Le football"], ["الملاكمة", "La boxe"], ["ألعاب القوى", "L'athlétisme"], ["التنس", "Le tennis"]], 2),
    Q("sp6", "sport", 1, "كم عدد لاعبي فريق كرة السلة داخل الملعب؟", "Combien de joueurs par équipe sont sur le terrain au basket ?",
      [["5", "5"], ["6", "6"], ["7", "7"], ["11", "11"]], 0),
    Q("sp7", "sport", 3, "ما هي مسافة سباق الماراثون؟", "Quelle est la distance d'un marathon ?",
      [["21,1 كلم", "21,1 km"], ["40 كلم", "40 km"], ["42,195 كلم", "42,195 km"], ["50 كلم", "50 km"]], 2),
    Q("sp8", "sport", 2, "أي بطولة تنس تُلعب على الملاعب الترابية؟", "Quel tournoi du Grand Chelem se joue sur terre battue ?",
      [["ويمبلدون", "Wimbledon"], ["رولان غاروس", "Roland-Garros"], ["أمريكا المفتوحة", "L'US Open"], ["أستراليا المفتوحة", "L'Open d'Australie"]], 1),

    // المغرب / Maroc
    Q("m1", "morocco", 1, "ما اسم الطبق المغربي الذي يُطهى في إناء فخاري مخروطي؟", "Quel plat marocain cuit dans un plat en terre conique ?",
      [["الكسكس", "Le couscous"], ["الطاجين", "Le tajine"], ["الحريرة", "La harira"], ["البسطيلة", "La pastilla"]], 1),
    Q("m2", "morocco", 1, "في أي مدينة يوجد مسجد الحسن الثاني؟", "Dans quelle ville se trouve la mosquée Hassan II ?",
      [["الرباط", "Rabat"], ["طنجة", "Tanger"], ["الدار البيضاء", "Casablanca"], ["أكادير", "Agadir"]], 2),
    Q("m3", "morocco", 1, "أي مدينة مغربية تُلقب بالمدينة الزرقاء؟", "Quelle ville marocaine est surnommée la ville bleue ?",
      [["شفشاون", "Chefchaouen"], ["الصويرة", "Essaouira"], ["إفران", "Ifrane"], ["تطوان", "Tétouan"]], 0),
    Q("m4", "morocco", 1, "على أي محيط تقع مدينة أكادير؟", "Sur quel océan se trouve Agadir ?",
      [["الهندي", "L'océan Indien"], ["الهادئ", "Le Pacifique"], ["الأطلسي", "L'Atlantique"], ["البحر المتوسط", "La Méditerranée"]], 2),
    Q("m5", "morocco", 2, "في أي منطقة تنتشر شجرة الأركان بشكل خاص؟", "Dans quelle région l'arganier pousse-t-il surtout ?",
      [["الريف", "Le Rif"], ["سوس", "Le Souss"], ["الغرب", "Le Gharb"], ["الشرق", "L'Oriental"]], 1),
    Q("m6", "morocco", 1, "ما هي العملة المغربية؟", "Quelle est la monnaie du Maroc ?",
      [["الريال", "Le riyal"], ["الدينار", "Le dinar"], ["الدرهم", "Le dirham"], ["الفرنك", "Le franc"]], 2),
    Q("m7", "morocco", 3, "كم عدد جهات المغرب حسب التقسيم الجهوي لسنة 2015؟", "Combien de régions compte le Maroc depuis le découpage de 2015 ?",
      [["10", "10"], ["12", "12"], ["16", "16"], ["14", "14"]], 1),
    Q("m8", "morocco", 1, "في أي مدينة توجد ساحة جامع الفنا؟", "Dans quelle ville se trouve la place Jemaa el-Fna ?",
      [["فاس", "Fès"], ["مكناس", "Meknès"], ["مراكش", "Marrakech"], ["وجدة", "Oujda"]], 2),

    // ألغاز / Énigmes
    Q("r1", "riddles", 1, "له عقارب لكنه لا يلدغ، فما هو؟", "Il a des aiguilles mais ne pique pas. Qu'est-ce que c'est ?",
      [["القنفذ", "Le hérisson"], ["الساعة", "L'horloge"], ["الشجرة", "Le sapin"], ["البوصلة", "La boussole"]], 1),
    Q("r2", "riddles", 2, "شيء كلما جفف ازداد بللًا، فما هو؟", "Plus elle sèche, plus elle est mouillée. Qu'est-ce que c'est ?",
      [["المنشفة", "La serviette"], ["الإسفنجة", "L'éponge"], ["الغيمة", "Le nuage"], ["الشمس", "Le soleil"]], 0),
    Q("r3", "riddles", 2, "له رقبة وليس له رأس، فما هو؟", "Elle a un col mais pas de tête. Qu'est-ce que c'est ?",
      [["الجبل", "La montagne"], ["الزرافة", "La girafe"], ["القارورة", "La bouteille"], ["المظلة", "Le parapluie"]], 2),
    Q("r4", "riddles", 3, "كلما أخذت منه تركت وراءك أكثر، فما هو؟", "Plus tu en fais, plus tu en laisses derrière toi. Qu'est-ce que c'est ?",
      [["الخطوات", "Les pas"], ["المال", "L'argent"], ["الوقت", "Le temps"], ["الكلمات", "Les mots"]], 0),
    Q("r5", "riddles", 2, "شيء يرتفع ولا ينزل أبدًا، فما هو؟", "Quelque chose monte et ne redescend jamais. Qu'est-ce que c'est ?",
      [["الدخان", "La fumée"], ["العمر", "L'âge"], ["الطائرة", "L'avion"], ["المصعد", "L'ascenseur"]], 1),
    Q("r6", "riddles", 1, "له أسنان ولا يعض، فما هو؟", "Il a des dents mais ne mord pas. Qu'est-ce que c'est ?",
      [["المشط", "Le peigne"], ["القط", "Le chat"], ["الكتاب", "Le livre"], ["الحذاء", "La chaussure"]], 0),
    Q("r7", "riddles", 2, "يمشي بلا أرجل ويبكي بلا عيون، فما هو؟", "Il avance sans pieds et pleure sans yeux. Qu'est-ce que c'est ?",
      [["الريح", "Le vent"], ["السحاب", "Le nuage"], ["النهر", "La rivière"], ["الظل", "L'ombre"]], 1),
    Q("r8", "riddles", 3, "ما هو الشيء الذي ينكسر إذا نطقت باسمه؟", "Qu'est-ce qui se brise dès qu'on prononce son nom ?",
      [["الزجاج", "Le verre"], ["الصمت", "Le silence"], ["الوعد", "La promesse"], ["البيضة", "L'œuf"]], 1)
  ];

  function C(id, points, seconds, ar, fr) {
    return { id: id, points: points, seconds: seconds, ar: ar, fr: fr };
  }

  var challenges = [
    C("c1", 2, 10, "اذكر خمس مدن مغربية في 10 ثوانٍ.", "Cite cinq villes marocaines en 10 secondes."),
    C("c2", 2, 30, "قلّد حيوانًا دون كلام، وعلى الآخرين أن يخمنوه في 30 ثانية.", "Imite un animal sans parler : les autres doivent deviner en 30 secondes."),
    C("c3", 1, 0, "غنِّ مقطعًا من أغنيتك المفضلة.", "Chante le refrain de ta chanson préférée."),
    C("c4", 2, 15, "اذكر ستة أنواع من الفواكه في 15 ثانية.", "Cite six fruits en 15 secondes."),
    C("c5", 2, 30, "قف على رجل واحدة لمدة 30 ثانية.", "Tiens-toi sur un pied pendant 30 secondes."),
    C("c6", 2, 0, "احكِ نكتة تُضحك لاعبًا واحدًا على الأقل.", "Raconte une blague qui fait rire au moins un joueur."),
    C("c7", 2, 30, "ارسم بيتًا وعيناك مغمضتان، ثم يحكم الآخرون.", "Dessine une maison les yeux fermés, puis les autres jugent."),
    C("c8", 2, 30, "مثّل مهنة بالإشارات، وعلى الآخرين تخمينها في 30 ثانية.", "Mime un métier : les autres doivent deviner en 30 secondes."),
    C("c9", 3, 10, "عُدّ من 1 إلى 20 بالفرنسية دون خطأ في 10 ثوانٍ.", "Compte de 1 à 20 en français sans erreur en 10 secondes."),
    C("c10", 3, 0, "ردّد ثلاث مرات بسرعة: «Les chaussettes de l'archiduchesse sont-elles sèches, archi-sèches ?»", "Répète trois fois vite : « Les chaussettes de l'archiduchesse sont-elles sèches, archi-sèches ? »"),
    C("c11", 2, 30, "أضحك المجموعة دون أن تتكلم خلال 30 ثانية.", "Fais rire le groupe sans parler en 30 secondes."),
    C("c12", 2, 15, "اذكر خمس دول يبدأ اسمها بحرف الميم في 15 ثانية.", "Cite cinq pays qui commencent par la lettre M en 15 secondes."),
    C("c13", 2, 0, "صف فيلمك المفضل بثلاث كلمات فقط، وعلى الآخرين تخمينه.", "Décris ton film préféré en trois mots : les autres doivent le deviner."),
    C("c14", 1, 0, "قم بعشر حركات قرفصاء.", "Fais dix squats."),
    C("c15", 1, 0, "قل مجاملة صادقة لكل لاعب.", "Fais un compliment sincère à chaque joueur."),
    C("c16", 3, 30, "تحدث 30 ثانية عن شيء في الغرفة دون أن تتوقف أو تقول «آآ».", "Parle 30 secondes d'un objet de la pièce sans t'arrêter ni dire « euh »."),
    C("c17", 2, 15, "اذكر خمسة حيوانات تعيش في البحر في 15 ثانية.", "Cite cinq animaux marins en 15 secondes."),
    C("c18", 2, 0, "ضع كتابًا على رأسك وامشِ من طرف الغرفة إلى الطرف الآخر دون أن يسقط.", "Traverse la pièce avec un livre sur la tête sans le faire tomber."),
    C("c19", 2, 0, "تهجَّ اسمك الكامل بالمقلوب.", "Épelle ton nom complet à l'envers."),
    C("c20", 3, 60, "ألّف بيتين من الشعر عن اللاعب الذي على يمينك في دقيقة.", "Invente deux vers rimés sur le joueur à ta droite en une minute."),
    C("c21", 2, 30, "دندن لحن أغنية دون كلمات، وعلى الآخرين معرفة عنوانها.", "Fredonne une chanson sans les paroles : les autres doivent trouver le titre."),
    C("c22", 3, 30, "حافظ على جدية وجهك 30 ثانية بينما يحاول الآخرون إضحاكك.", "Garde ton sérieux 30 secondes pendant que les autres essaient de te faire rire."),
    C("c23", 2, 15, "قل «شكرًا» بخمس لغات مختلفة في 15 ثانية.", "Dis « merci » dans cinq langues différentes en 15 secondes."),
    C("c24", 2, 0, "قلّد صوت شخصية مشهورة يعرفها الجميع، وعلى الآخرين تخمينها.", "Imite la voix d'un personnage célèbre : les autres doivent deviner qui c'est.")
  ];

  var data = { categories: categories, questions: questions, challenges: challenges };
  if (typeof module === "object" && module.exports) module.exports = data;
  else root.GAME_DATA = data;
})(this);
