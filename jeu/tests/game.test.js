// node --test jeu/tests/game.test.js
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const DATA = require("../data.js");
const L = require("../logic.js");

test("chaque question est bilingue, a 4 options et une réponse valide", () => {
  const ids = new Set();
  const cats = new Set(DATA.categories.map((c) => c.id));
  for (const q of DATA.questions) {
    assert.ok(!ids.has(q.id), "id en double " + q.id);
    ids.add(q.id);
    assert.ok(cats.has(q.cat), q.id);
    assert.ok(q.ar && q.fr, q.id);
    assert.ok([1, 2, 3].includes(q.level), q.id);
    assert.strictEqual(q.options.length, 4, q.id);
    q.options.forEach((o) => assert.ok(o[0] && o[1], q.id));
    assert.strictEqual(new Set(q.options.map((o) => o[1])).size, 4, "options en double " + q.id);
    assert.ok(q.answer >= 0 && q.answer < 4, q.id);
  }
  for (const c of DATA.categories) {
    assert.ok(DATA.questions.filter((q) => q.cat === c.id).length >= 5, c.id);
  }
});

test("chaque défi est bilingue avec des points", () => {
  const ids = new Set();
  for (const c of DATA.challenges) {
    assert.ok(!ids.has(c.id));
    ids.add(c.id);
    assert.ok(c.ar && c.fr && c.points > 0 && c.seconds >= 0, c.id);
  }
});

test("validation des joueurs et des options", () => {
  assert.throws(() => L.createGame(DATA, { players: [" "] }), /no_players/);
  assert.throws(() => L.createGame(DATA, { players: ["Amine", "amine"] }), /duplicate_player/);
  assert.throws(() => L.createGame(DATA, { players: Array.from({ length: 9 }, (_, i) => "J" + i) }), /too_many_players/);
  assert.throws(() => L.createGame(DATA, { players: ["A"], categories: ["inconnue"] }), /no_questions/);
  const g = L.createGame(DATA, { players: ["A"], mode: "questions" });
  assert.throws(() => L.drawCard(g, DATA, "challenge"), /type_not_allowed/);
});

test("bonne réponse : points du niveau, bonus toutes les 3 d'affilée", () => {
  const rng = L.seededRng(1);
  const g = L.createGame(DATA, { players: ["Solo"], mode: "questions", rounds: 4 }, rng);
  let expected = 0;
  for (let i = 1; i <= 3; i++) {
    L.drawCard(g, DATA, "question", rng);
    const q = L.currentCard(g, DATA);
    const r = L.answerQuestion(g, DATA, g.current.order.indexOf(q.answer));
    assert.ok(r.correct);
    expected += q.level + (i === 3 ? 1 : 0);
    assert.strictEqual(r.bonus, i === 3 ? 1 : 0);
  }
  assert.strictEqual(g.players[0].score, expected);
  L.drawCard(g, DATA, "question", rng);
  const r = L.answerQuestion(g, DATA, null);
  assert.ok(!r.correct && r.timeout);
  assert.strictEqual(g.players[0].streak, 0);
  assert.strictEqual(g.players[0].score, expected);
  assert.ok(g.over);
});

test("tours, manches, défis, joker et classement", () => {
  const rng = L.seededRng(7);
  const g = L.createGame(DATA, { players: ["A", "B", "C"], mode: "challenges", rounds: 2 }, rng);
  assert.strictEqual(L.currentPlayer(g).name, "A");
  L.drawCard(g, DATA, "challenge", rng);
  const before = g.current.id;
  L.useJoker(g, DATA, rng);
  assert.notStrictEqual(g.current.id, before);
  assert.strictEqual(g.players[0].jokers, L.JOKERS_PER_PLAYER - 1);
  assert.strictEqual(L.currentPlayer(g).name, "A", "le joker garde le tour");
  const pts = L.currentCard(g, DATA).points;
  L.resolveChallenge(g, DATA, true);
  assert.strictEqual(g.players[0].score, pts);
  assert.strictEqual(L.currentPlayer(g).name, "B");
  L.drawCard(g, DATA, "challenge", rng);
  L.resolveChallenge(g, DATA, false);
  L.drawCard(g, DATA, "challenge", rng);
  L.resolveChallenge(g, DATA, false);
  assert.strictEqual(g.round, 2);
  assert.strictEqual(L.currentPlayer(g).name, "A");
  for (let i = 0; i < 3; i++) { L.drawCard(g, DATA, "challenge", rng); L.resolveChallenge(g, DATA, false); }
  assert.ok(g.over);
  assert.throws(() => L.drawCard(g, DATA, "challenge", rng), /game_over/);
  const rk = L.ranking(g);
  assert.deepStrictEqual(rk.map((r) => r.rank), [1, 2, 2]);
  assert.strictEqual(rk[0].name, "A");
});

test("le paquet est remélangé quand il est épuisé", () => {
  const rng = L.seededRng(3);
  const g = L.createGame(DATA, { players: ["A"], mode: "questions", categories: ["sport"], rounds: 20 }, rng);
  const n = DATA.questions.filter((q) => q.cat === "sport").length;
  const seen = new Set();
  for (let i = 0; i < n; i++) { L.drawCard(g, DATA, "question", rng); seen.add(g.current.id); L.answerQuestion(g, DATA, 0); }
  assert.strictEqual(seen.size, n, "aucune répétition avant épuisement");
  L.drawCard(g, DATA, "question", rng);
  assert.ok(seen.has(g.current.id));
});
