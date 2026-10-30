// Interface du jeu : écrans de configuration, tour, carte, résultat et classement.
(function () {
  "use strict";

  var DATA = window.GAME_DATA;
  var L = window.GameLogic;
  var QUESTION_SECONDS = 20;
  var SAVE_KEY = "jeu-questions-defis:v1";

  var T = {
    title: ["أسئلة وتحديات", "Questions et défis"],
    lang: ["Français", "العربية"],
    players: ["اللاعبون", "Joueurs"],
    playerName: ["اسم اللاعب", "Nom du joueur"],
    add: ["إضافة", "Ajouter"],
    remove: ["حذف", "Retirer"],
    mode: ["نوع اللعب", "Mode de jeu"],
    mixed: ["أسئلة وتحديات", "Questions et défis"],
    questions: ["أسئلة فقط", "Questions seulement"],
    challenges: ["تحديات فقط", "Défis seulement"],
    categories: ["الفئات", "Catégories"],
    rounds: ["عدد الجولات", "Nombre de manches"],
    timer: ["مؤقت للأسئلة (20 ثانية)", "Minuteur pour les questions (20 s)"],
    start: ["ابدأ اللعب", "Commencer"],
    resume: ["متابعة اللعبة السابقة", "Reprendre la partie"],
    round: ["الجولة", "Manche"],
    turnOf: ["دور", "Au tour de"],
    pickQ: ["سؤال", "Question"],
    pickC: ["تحدي", "Défi"],
    joker: ["جوكر", "Joker"],
    level: ["المستوى", "Niveau"],
    pts: ["نقطة", "pt"],
    startTimer: ["ابدأ المؤقت", "Lancer le minuteur"],
    success: ["نجح", "Réussi"],
    fail: ["فشل", "Raté"],
    judge: ["يقرر باقي اللاعبين هل نجح التحدي", "Les autres joueurs décident si le défi est réussi"],
    right: ["إجابة صحيحة!", "Bonne réponse !"],
    wrong: ["إجابة خاطئة", "Mauvaise réponse"],
    timeout: ["انتهى الوقت", "Temps écoulé"],
    answerWas: ["الإجابة الصحيحة", "La bonne réponse"],
    won: ["تحدٍّ ناجح!", "Défi réussi !"],
    lost: ["تحدٍّ فاشل", "Défi raté"],
    streak: ["مكافأة سلسلة", "Bonus de série"],
    next: ["التالي", "Suivant"],
    results: ["النتائج النهائية", "Classement final"],
    again: ["إعادة بنفس اللاعبين", "Rejouer avec les mêmes joueurs"],
    newGame: ["لعبة جديدة", "Nouvelle partie"],
    quit: ["إنهاء اللعبة", "Terminer la partie"],
    quitConfirm: ["هل تريد إنهاء اللعبة الآن؟", "Terminer la partie maintenant ?"],
    stats: ["صحيحة / خاطئة · تحديات ناجحة", "Bonnes / mauvaises · défis réussis"],
    err_no_players: ["أضف لاعبًا واحدًا على الأقل.", "Ajoute au moins un joueur."],
    err_too_many_players: ["الحد الأقصى 8 لاعبين.", "8 joueurs au maximum."],
    err_duplicate_player: ["هذا الاسم موجود مسبقًا.", "Ce nom est déjà pris."],
    err_no_questions: ["اختر فئة واحدة على الأقل.", "Choisis au moins une catégorie."]
  };

  var lang = load("lang") || "ar";
  var app = document.getElementById("app");
  var state = null;
  var setup = { players: [], mode: "mixed", categories: DATA.categories.map(function (c) { return c.id; }), rounds: 5, timer: true };
  var timerId = null;

  function load(k) { try { return localStorage.getItem(SAVE_KEY + ":" + k); } catch (e) { return null; } }
  function save(k, v) { try { if (v == null) localStorage.removeItem(SAVE_KEY + ":" + k); else localStorage.setItem(SAVE_KEY + ":" + k, v); } catch (e) { /* stockage indisponible */ } }
  function saveGame() { save("game", state && !state.over ? JSON.stringify({ state: state, setup: setup }) : null); }

  try {
    var saved = JSON.parse(load("setup") || "null");
    if (saved) setup = Object.assign(setup, saved);
  } catch (e) { /* ignorer */ }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]; });
  }
  // Texte bilingue : langue principale, puis l'autre en petit.
  function bi(pair) {
    var main = lang === "ar" ? pair[0] : pair[1], other = lang === "ar" ? pair[1] : pair[0];
    if (main === other) return esc(main);
    var otherDir = lang === "ar" ? "ltr" : "rtl";
    return esc(main) + '<span class="sub" dir="' + otherDir + '">' + esc(other) + "</span>";
  }
  function t(key) { return bi(T[key]); }
  function one(key) { return esc(lang === "ar" ? T[key][0] : T[key][1]); }
  function item(obj) { return bi([obj.ar, obj.fr]); }

  function applyLang() {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.getElementById("app-title").innerHTML = one("title");
    document.title = lang === "ar" ? T.title[0] : T.title[1];
    document.getElementById("lang-toggle").textContent = lang === "ar" ? T.lang[0] : T.lang[1];
  }
  document.getElementById("lang-toggle").addEventListener("click", function () {
    lang = lang === "ar" ? "fr" : "ar";
    save("lang", lang);
    applyLang();
    render();
  });

  function stopTimer() { if (timerId) { clearInterval(timerId); timerId = null; } }
  function startCountdown(seconds, onTick, onEnd) {
    stopTimer();
    var end = Date.now() + seconds * 1000;
    function tick() {
      var left = Math.max(0, (end - Date.now()) / 1000);
      onTick(left, seconds);
      if (left <= 0) { stopTimer(); onEnd(); }
    }
    tick();
    timerId = setInterval(tick, 250);
  }
  function paintTimer(left, total) {
    var bar = document.querySelector(".timer > div"), label = document.querySelector(".timer-label");
    if (bar) bar.style.width = (100 * left / total) + "%";
    if (label) label.textContent = Math.ceil(left) + " s";
  }

  // ---------- Écrans ----------
  var view = "setup", lastResult = null;

  function render() {
    stopTimer();
    if (view === "setup") renderSetup();
    else if (view === "turn") renderTurn();
    else if (view === "card") renderCard();
    else if (view === "result") renderResult();
    else if (view === "end") renderEnd();
  }

  function renderSetup() {
    var resumable = load("game");
    var html = "";
    if (resumable) html += '<button class="big" id="resume">' + t("resume") + "</button><p></p>";
    html += '<section class="card"><h2>' + t("players") + "</h2>" +
      '<form id="add-form" class="row"><input type="text" id="pname" maxlength="20" autocomplete="off" placeholder="' + one("playerName") + '">' +
      '<button type="submit" style="flex:0 0 auto">' + one("add") + "</button></form>" +
      '<ul class="players">' + setup.players.map(function (p, i) {
        return "<li><span>" + esc(p) + '</span><button class="ghost" data-remove="' + i + '">' + one("remove") + "</button></li>";
      }).join("") + "</ul></section>";

    html += '<section class="card"><h2>' + t("mode") + '</h2><div class="chips">' +
      ["mixed", "questions", "challenges"].map(function (m) {
        return '<label class="chip"><input type="radio" name="mode" value="' + m + '"' + (setup.mode === m ? " checked" : "") + "> " + one(m) + "</label>";
      }).join("") + "</div></section>";

    html += '<section class="card"' + (setup.mode === "challenges" ? " hidden" : "") + "><h2>" + t("categories") + '</h2><div class="chips">' +
      DATA.categories.map(function (c) {
        var n = DATA.questions.filter(function (q) { return q.cat === c.id; }).length;
        return '<label class="chip"><input type="checkbox" name="cat" value="' + c.id + '"' + (setup.categories.indexOf(c.id) >= 0 ? " checked" : "") + "> " +
          c.icon + " " + esc(lang === "ar" ? c.ar : c.fr) + ' <small class="muted">(' + n + ")</small></label>";
      }).join("") + '</div><p></p><label class="chip"><input type="checkbox" id="timer"' + (setup.timer ? " checked" : "") + "> " + one("timer") + "</label></section>";

    html += '<section class="card"><h2>' + t("rounds") + '</h2><div class="chips">' +
      [3, 5, 8, 10].map(function (r) {
        return '<label class="chip"><input type="radio" name="rounds" value="' + r + '"' + (setup.rounds === r ? " checked" : "") + "> " + r + "</label>";
      }).join("") + "</div></section>";

    html += '<button class="primary big" id="start">' + t("start") + '</button><p class="error" id="err"></p>';
    app.innerHTML = html;

    var input = document.getElementById("pname");
    document.getElementById("add-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var name = input.value.trim();
      if (!name) return;
      if (setup.players.some(function (p) { return p.toLowerCase() === name.toLowerCase(); })) return showError("duplicate_player");
      if (setup.players.length >= L.MAX_PLAYERS) return showError("too_many_players");
      setup.players.push(name);
      persistSetup();
      render();
      document.getElementById("pname").focus();
    });
    app.querySelectorAll("[data-remove]").forEach(function (b) {
      b.addEventListener("click", function () { setup.players.splice(+b.dataset.remove, 1); persistSetup(); render(); });
    });
    app.querySelectorAll('input[name="mode"]').forEach(function (r) {
      r.addEventListener("change", function () { setup.mode = r.value; persistSetup(); render(); });
    });
    app.querySelectorAll('input[name="rounds"]').forEach(function (r) {
      r.addEventListener("change", function () { setup.rounds = +r.value; persistSetup(); });
    });
    app.querySelectorAll('input[name="cat"]').forEach(function (c) {
      c.addEventListener("change", function () {
        setup.categories = Array.prototype.filter.call(app.querySelectorAll('input[name="cat"]'), function (x) { return x.checked; }).map(function (x) { return x.value; });
        persistSetup();
      });
    });
    document.getElementById("timer").addEventListener("change", function (e) { setup.timer = e.target.checked; persistSetup(); });
    document.getElementById("start").addEventListener("click", function () { startGame(); });
    var resume = document.getElementById("resume");
    if (resume) resume.addEventListener("click", function () {
      try {
        var g = JSON.parse(resumable);
        state = g.state; setup = Object.assign(setup, g.setup);
        view = state.current ? "card" : "turn";
        render();
      } catch (e) { save("game", null); render(); }
    });
  }

  function persistSetup() { save("setup", JSON.stringify(setup)); }
  function showError(code) {
    var el = document.getElementById("err");
    if (el) el.innerHTML = T["err_" + code] ? t("err_" + code) : esc(code);
  }

  function startGame() {
    // Un nom tapé mais pas encore ajouté compte aussi.
    var pending = document.getElementById("pname");
    if (pending && pending.value.trim() && setup.players.length < L.MAX_PLAYERS &&
        !setup.players.some(function (p) { return p.toLowerCase() === pending.value.trim().toLowerCase(); })) {
      setup.players.push(pending.value.trim());
      persistSetup();
    }
    try {
      state = L.createGame(DATA, { players: setup.players, mode: setup.mode, categories: setup.categories, rounds: setup.rounds });
    } catch (e) { return showError(e.message); }
    view = "turn";
    saveGame();
    render();
  }

  function scoreboard() {
    return '<div class="scoreboard">' + state.players.map(function (p, i) {
      return '<div class="score' + (i === state.turn && !state.over ? " active" : "") + '"><small>' + esc(p.name) + "</small><b>" + p.score + "</b>" +
        "<small>🃏 " + p.jokers + (p.streak >= 2 ? " · 🔥" + p.streak : "") + "</small></div>";
    }).join("") + "</div>";
  }

  function header() {
    var p = L.currentPlayer(state);
    return scoreboard() + '<div class="turn-head"><span class="badge">' + one("round") + " " + state.round + " / " + state.roundsTotal + "</span>" +
      '<div class="muted">' + one("turnOf") + '</div><div class="who">' + esc(p.name) + "</div></div>";
  }

  function renderTurn() {
    var types = L.allowedTypes(state);
    var html = header() + '<section class="card"><div class="choice"' + (types.length === 1 ? ' style="grid-template-columns:1fr"' : "") + ">";
    if (types.indexOf("question") >= 0) html += '<button class="q" data-type="question">❓ ' + t("pickQ") + "</button>";
    if (types.indexOf("challenge") >= 0) html += '<button class="c" data-type="challenge">🔥 ' + t("pickC") + "</button>";
    html += '</div></section><button class="ghost" id="quit">' + one("quit") + "</button>";
    app.innerHTML = html;
    app.querySelectorAll("[data-type]").forEach(function (b) {
      b.addEventListener("click", function () { L.drawCard(state, DATA, b.dataset.type); view = "card"; saveGame(); render(); });
    });
    document.getElementById("quit").addEventListener("click", quit);
  }

  function quit() {
    if (!window.confirm(lang === "ar" ? T.quitConfirm[0] : T.quitConfirm[1])) return;
    state.over = true; state.current = null;
    view = "end"; saveGame(); render();
  }

  function jokerButton() {
    var p = L.currentPlayer(state);
    return '<button id="joker"' + (p.jokers ? "" : " disabled") + ">🃏 " + one("joker") + " (" + p.jokers + ")</button>";
  }
  function bindJoker() {
    var j = document.getElementById("joker");
    if (j) j.addEventListener("click", function () { L.useJoker(state, DATA); saveGame(); render(); });
  }

  function renderCard() {
    var card = L.currentCard(state, DATA);
    if (state.current.type === "question") {
      var cat = DATA.categories.filter(function (c) { return c.id === card.cat; })[0];
      var html = header() + '<section class="card"><div class="row" style="justify-content:space-between">' +
        '<span class="badge" style="flex:0 0 auto">' + cat.icon + " " + esc(lang === "ar" ? cat.ar : cat.fr) + "</span>" +
        '<span class="badge" style="flex:0 0 auto">' + "★".repeat(card.level) + " · " + card.level + " " + one("pts") + "</span></div>" +
        '<div class="prompt">' + item(card) + "</div>";
      if (setup.timer) html += '<div class="timer"><div style="width:100%"></div></div><div class="timer-label muted"></div>';
      html += '<div class="options">' + state.current.order.map(function (orig, shown) {
        var o = card.options[orig];
        return '<button data-opt="' + shown + '">' + bi([o[0], o[1]]) + "</button>";
      }).join("") + "</div></section>" + jokerButton();
      app.innerHTML = html;
      app.querySelectorAll("[data-opt]").forEach(function (b) {
        b.addEventListener("click", function () { finishQuestion(+b.dataset.opt); });
      });
      bindJoker();
      if (setup.timer) startCountdown(QUESTION_SECONDS, paintTimer, function () { finishQuestion(null); });
    } else {
      var h = header() + '<section class="card"><span class="badge">🔥 ' + one("pickC") + " · " + card.points + " " + one("pts") + "</span>" +
        '<div class="prompt">' + item(card) + "</div>";
      if (card.seconds) h += '<div class="timer"><div style="width:100%"></div></div><div class="timer-label muted">' + card.seconds + ' s</div>' +
        '<p><button id="go">⏱️ ' + one("startTimer") + "</button></p>";
      h += '<p class="muted">' + t("judge") + '</p><div class="row"><button class="primary" id="ok">✅ ' + one("success") + '</button>' +
        '<button id="ko">❌ ' + one("fail") + "</button></div></section>" + jokerButton();
      app.innerHTML = h;
      var go = document.getElementById("go");
      if (go) go.addEventListener("click", function () {
        go.disabled = true;
        startCountdown(card.seconds, paintTimer, function () { if (navigator.vibrate) navigator.vibrate(300); });
      });
      document.getElementById("ok").addEventListener("click", function () { finishChallenge(true); });
      document.getElementById("ko").addEventListener("click", function () { finishChallenge(false); });
      bindJoker();
    }
  }

  function finishQuestion(shown) {
    stopTimer();
    var card = L.currentCard(state, DATA), order = state.current.order;
    lastResult = L.answerQuestion(state, DATA, shown);
    lastResult.card = card; lastResult.order = order; lastResult.shown = shown;
    view = "result"; saveGame(); render();
  }
  function finishChallenge(ok) {
    stopTimer();
    lastResult = L.resolveChallenge(state, DATA, ok);
    view = "result"; saveGame(); render();
  }

  function renderResult() {
    var r = lastResult, html = scoreboard() + '<section class="card">';
    if (r.type === "question") {
      html += '<div class="verdict ' + (r.correct ? "ok" : "ko") + '">' + (r.correct ? t("right") : r.timeout ? t("timeout") : t("wrong")) + "</div>" +
        '<div class="prompt">' + item(r.card) + '</div><div class="options">' + r.order.map(function (orig, shown) {
          var o = r.card.options[orig], cls = orig === r.answer ? "right" : shown === r.shown ? "wrong" : "";
          return '<button disabled class="' + cls + '">' + bi([o[0], o[1]]) + "</button>";
        }).join("") + "</div>";
    } else {
      html += '<div class="verdict ' + (r.correct ? "ok" : "ko") + '">' + (r.correct ? t("won") : t("lost")) + "</div>";
    }
    html += '<p class="verdict">' + esc(r.player) + ' <span dir="ltr">+' + (r.points + r.bonus) + "</span></p>";
    if (r.bonus) html += '<p style="text-align:center">🔥 ' + one("streak") + ' <span dir="ltr">+' + r.bonus + "</span></p>";
    html += '</section><button class="primary big" id="next">' + t("next") + "</button>";
    app.innerHTML = html;
    document.getElementById("next").addEventListener("click", function () { view = state.over ? "end" : "turn"; render(); });
    document.getElementById("next").focus();
  }

  function renderEnd() {
    var medals = ["🥇", "🥈", "🥉"];
    var html = '<section class="card"><h2>' + t("results") + '</h2><ol class="podium">' + L.ranking(state).map(function (r) {
      var p = state.players.filter(function (x) { return x.name === r.name; })[0];
      return "<li><span>" + (medals[r.rank - 1] || r.rank + ".") + " " + esc(r.name) +
        ' <small class="muted">' + p.correct + " / " + p.wrong + " · " + p.challengesWon + "</small></span><b>" + r.score + "</b></li>";
    }).join("") + '</ol><p class="muted">' + t("stats") + "</p></section>" +
      '<button class="primary big" id="again">' + t("again") + '</button><p></p><button class="big" id="new">' + t("newGame") + "</button>";
    app.innerHTML = html;
    save("game", null);
    document.getElementById("again").addEventListener("click", function () {
      state = L.createGame(DATA, { players: setup.players, mode: setup.mode, categories: setup.categories, rounds: setup.rounds });
      view = "turn"; saveGame(); render();
    });
    document.getElementById("new").addEventListener("click", function () { state = null; view = "setup"; render(); });
  }

  applyLang();
  render();
})();
