// Règles du jeu, sans DOM : utilisable dans le navigateur (window.GameLogic) et sous Node (tests).
(function (root) {
  "use strict";

  var MAX_PLAYERS = 8;
  var JOKERS_PER_PLAYER = 2;
  var STREAK_BONUS_EVERY = 3; // +1 point toutes les 3 bonnes réponses d'affilée

  // Générateur pseudo-aléatoire reproductible (mulberry32), pour les tests.
  function seededRng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffle(list, rng) {
    var a = list.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  // opts : { players: [noms], mode: "mixed"|"questions"|"challenges", categories: [ids], rounds }
  function createGame(data, opts, rng) {
    rng = rng || Math.random;
    var names = (opts.players || []).map(function (n) { return String(n).trim(); }).filter(Boolean);
    if (names.length < 1) throw new Error("no_players");
    if (names.length > MAX_PLAYERS) throw new Error("too_many_players");
    var seen = {};
    names.forEach(function (n) {
      var k = n.toLowerCase();
      if (seen[k]) throw new Error("duplicate_player");
      seen[k] = true;
    });

    var mode = opts.mode || "mixed";
    if (["mixed", "questions", "challenges"].indexOf(mode) < 0) throw new Error("bad_mode");
    var cats = opts.categories && opts.categories.length ? opts.categories : data.categories.map(function (c) { return c.id; });
    var qIds = data.questions.filter(function (q) { return cats.indexOf(q.cat) >= 0; }).map(function (q) { return q.id; });
    if (mode !== "challenges" && qIds.length === 0) throw new Error("no_questions");
    var rounds = Math.max(1, Math.min(20, parseInt(opts.rounds, 10) || 5));

    return {
      players: names.map(function (n) {
        return { name: n, score: 0, jokers: JOKERS_PER_PLAYER, streak: 0, correct: 0, wrong: 0, challengesWon: 0, challengesLost: 0 };
      }),
      mode: mode,
      categories: cats,
      roundsTotal: rounds,
      round: 1,
      turn: 0,
      qDeck: shuffle(qIds, rng),
      cDeck: shuffle(data.challenges.map(function (c) { return c.id; }), rng),
      allQ: qIds,
      current: null,
      over: false
    };
  }

  function currentPlayer(state) {
    return state.players[state.turn];
  }

  function findById(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function allowedTypes(state) {
    if (state.mode === "questions") return ["question"];
    if (state.mode === "challenges") return ["challenge"];
    return ["question", "challenge"];
  }

  // Tire une carte du type demandé ; le paquet est remélangé quand il est épuisé.
  function drawCard(state, data, type, rng) {
    rng = rng || Math.random;
    if (state.over) throw new Error("game_over");
    if (allowedTypes(state).indexOf(type) < 0) throw new Error("type_not_allowed");
    var id;
    if (type === "question") {
      if (!state.qDeck.length) state.qDeck = shuffle(state.allQ, rng);
      id = state.qDeck.shift();
      state.current = { type: "question", id: id, order: shuffle([0, 1, 2, 3], rng) };
    } else {
      if (!state.cDeck.length) state.cDeck = shuffle(data.challenges.map(function (c) { return c.id; }), rng);
      id = state.cDeck.shift();
      state.current = { type: "challenge", id: id };
    }
    return state.current;
  }

  function currentCard(state, data) {
    if (!state.current) return null;
    return findById(state.current.type === "question" ? data.questions : data.challenges, state.current.id);
  }

  function advance(state) {
    state.current = null;
    state.turn += 1;
    if (state.turn >= state.players.length) {
      state.turn = 0;
      state.round += 1;
    }
    if (state.round > state.roundsTotal) state.over = true;
  }

  // shownIndex : position de l'option affichée (selon state.current.order), ou null si le temps est écoulé.
  function answerQuestion(state, data, shownIndex) {
    if (!state.current || state.current.type !== "question") throw new Error("no_question");
    var q = findById(data.questions, state.current.id);
    var p = currentPlayer(state);
    var picked = shownIndex == null ? null : state.current.order[shownIndex];
    var correct = picked === q.answer;
    var points = 0, bonus = 0;
    if (correct) {
      p.streak += 1;
      p.correct += 1;
      points = q.level;
      if (p.streak % STREAK_BONUS_EVERY === 0) bonus = 1;
    } else {
      p.streak = 0;
      p.wrong += 1;
    }
    p.score += points + bonus;
    var result = {
      type: "question", player: p.name, correct: correct, timeout: shownIndex == null,
      points: points, bonus: bonus, answer: q.answer, shownAnswer: state.current.order.indexOf(q.answer)
    };
    advance(state);
    return result;
  }

  function resolveChallenge(state, data, success) {
    if (!state.current || state.current.type !== "challenge") throw new Error("no_challenge");
    var c = findById(data.challenges, state.current.id);
    var p = currentPlayer(state);
    var points = success ? c.points : 0;
    if (success) p.challengesWon += 1; else p.challengesLost += 1;
    p.score += points;
    var result = { type: "challenge", player: p.name, correct: !!success, points: points, bonus: 0 };
    advance(state);
    return result;
  }

  // Joker : remplace la carte en cours par une autre du même type, sans perdre son tour.
  function useJoker(state, data, rng) {
    if (!state.current) throw new Error("no_card");
    var p = currentPlayer(state);
    if (p.jokers <= 0) throw new Error("no_jokers");
    p.jokers -= 1;
    return drawCard(state, data, state.current.type, rng);
  }

  // Classement : score décroissant, ex æquo au même rang (1, 1, 3...).
  function ranking(state) {
    var sorted = state.players.slice().sort(function (a, b) { return b.score - a.score; });
    var rank = 0;
    return sorted.map(function (p, i) {
      if (i === 0 || p.score !== sorted[i - 1].score) rank = i + 1;
      return { rank: rank, name: p.name, score: p.score };
    });
  }

  var api = {
    MAX_PLAYERS: MAX_PLAYERS, JOKERS_PER_PLAYER: JOKERS_PER_PLAYER, STREAK_BONUS_EVERY: STREAK_BONUS_EVERY,
    seededRng: seededRng, shuffle: shuffle, createGame: createGame, currentPlayer: currentPlayer,
    allowedTypes: allowedTypes, drawCard: drawCard, currentCard: currentCard, answerQuestion: answerQuestion,
    resolveChallenge: resolveChallenge, useJoker: useJoker, ranking: ranking
  };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GameLogic = api;
})(this);
