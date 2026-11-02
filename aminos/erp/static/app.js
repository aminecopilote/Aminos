"use strict";
// All text goes through textContent / value: nothing from the server is ever interpreted as HTML.
var STATUS = {nouveau: "Nouveau", devis: "Devis", en_cours: "En cours", a_relire: "À relire", certifie: "Certifié", livre: "Livré", facture: "Facturé", clos: "Clos"};
var DOC_STATUS = {draft: "Brouillon", sent: "Envoyé", accepted: "Accepté", paid: "Payé", "void": "Annulé"};
var LANGS = {ar: "Arabe", fr: "Français", en: "Anglais", nl: "Néerlandais"};
var me = null, csrf = "", tab = "dashboard", bsModal = null;

function h(tag, attrs) {
  var el = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) {
    if (k === "class") el.className = attrs[k];
    else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), attrs[k]);
    else if (k === "value") el.value = attrs[k];
    else el.setAttribute(k, attrs[k]);
  });
  function add(c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach(add); return; }
    el.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
  }
  for (var i = 2; i < arguments.length; i++) add(arguments[i]);
  return el;
}
function money(c, cur) { var s = c < 0 ? "-" : ""; c = Math.abs(c); return s + Math.floor(c / 100).toLocaleString("fr-FR") + "," + ("0" + (c % 100)).slice(-2) + " " + (cur || "MAD"); }
function toCents(v) { var n = parseFloat(String(v).replace(",", ".")); return isFinite(n) ? Math.round(n * 100) : NaN; }
function api(method, path, body) {
  var opt = {method: method, headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf}, credentials: "same-origin"};
  if (body !== undefined) opt.body = JSON.stringify(body);
  return fetch("/erp/api" + path, opt).then(function (r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      if (r.status === 401 && path !== "/login") { showLogin(); throw new Error("Session expirée"); }
      if (!r.ok) throw new Error(j.error || "Erreur " + r.status);
      return j;
    });
  });
}
function alertBox(msg, kind) { return h("div", {class: "alert alert-" + (kind || "danger")}, msg); }
function fail(e) { var v = document.getElementById("view"); v.insertBefore(alertBox(e.message), v.firstChild); }
function field(label, input) { return h("div", {class: "mb-2"}, h("label", {class: "form-label small mb-0"}, label), input); }
function input(type, name, value) { return h("input", {class: "form-control form-control-sm", type: type, name: name, value: value === undefined ? "" : value}); }
function select(name, opts, value) {
  var s = h("select", {class: "form-select form-select-sm", name: name});
  Object.keys(opts).forEach(function (k) { var o = h("option", {value: k}, opts[k]); if (k === String(value)) o.selected = true; s.appendChild(o); });
  return s;
}
function openModal(title, body) {
  document.getElementById("modal-title").textContent = title;
  var b = document.getElementById("modal-body"); b.textContent = ""; b.appendChild(body);
  if (!bsModal) bsModal = new bootstrap.Modal(document.getElementById("modal"));
  bsModal.show();
}
function closeModal() { if (bsModal) bsModal.hide(); }
function val(form, n) { return form.elements[n].value.trim(); }

// ---- login -----------------------------------------------------
function showLogin() {
  me = null; document.getElementById("topbar").hidden = true;
  var v = document.getElementById("view"); v.textContent = "";
  var form = h("form", {class: "mx-auto"}, h("h3", {}, "Connexion"),
    field("Identifiant", input("text", "username")), field("Mot de passe", input("password", "password")),
    h("button", {class: "btn btn-primary", type: "submit"}, "Se connecter"));
  form.style.maxWidth = "360px";
  var msg = h("div");
  form.addEventListener("submit", function (ev) {
    ev.preventDefault(); msg.textContent = "";
    api("POST", "/login", {username: val(form, "username"), password: form.elements.password.value}).then(function (j) {
      me = j; csrf = j.csrf; start();
    }).catch(function (e) { msg.appendChild(alertBox(e.message)); });
  });
  v.appendChild(form); v.appendChild(msg);
}
function start() {
  document.getElementById("topbar").hidden = false;
  document.getElementById("who").textContent = me.user + " · " + me.org;
  var t = document.getElementById("tabs"); t.textContent = "";
  [["dashboard", "Tableau de bord"], ["clients", "Clients"], ["cases", "Dossiers"], ["quote", "Devis"], ["invoice", "Factures"]].forEach(function (x) {
    var a = h("a", {class: "nav-link" + (x[0] === tab ? " active" : ""), href: "#"}, x[1]);
    a.addEventListener("click", function (ev) { ev.preventDefault(); tab = x[0]; start(); });
    t.appendChild(h("li", {class: "nav-item"}, a));
  });
  ({dashboard: viewDashboard, clients: viewClients, cases: viewCases, quote: viewDocs, invoice: viewDocs})[tab]();
}

// ---- dashboard -------------------------------------------------
function viewDashboard() {
  api("GET", "/dashboard").then(function (d) {
    var v = document.getElementById("view"); v.textContent = "";
    var cards = h("div", {class: "row g-3 mb-4"});
    Object.keys(STATUS).forEach(function (k) {
      cards.appendChild(h("div", {class: "col-6 col-md-3"}, h("div", {class: "card"}, h("div", {class: "card-body py-2"},
        h("div", {class: "small text-muted"}, STATUS[k]), h("div", {class: "fs-4"}, d.cases_by_status[k] || 0)))));
    });
    v.appendChild(cards);
    v.appendChild(h("p", {}, "Clients : ", h("strong", {}, d.clients), " · Encours à recevoir : ", h("strong", {}, money(d.outstanding_cents))));
    var late = h("table", {class: "table table-sm"}, h("thead", {}, h("tr", {}, h("th", {}, "Dossier"), h("th", {}, "Client"), h("th", {}, "Échéance"))), h("tbody"));
    d.late_cases.forEach(function (c) { late.tBodies[0].appendChild(h("tr", {}, h("td", {}, c.ref + " · " + c.title), h("td", {}, c.client_name), h("td", {}, c.deadline))); });
    v.appendChild(h("h5", {}, "Dossiers en retard")); v.appendChild(d.late_cases.length ? late : h("p", {class: "text-muted"}, "Aucun."));
    var od = h("table", {class: "table table-sm"}, h("thead", {}, h("tr", {}, h("th", {}, "Facture"), h("th", {}, "Client"), h("th", {}, "Échéance"), h("th", {class: "num"}, "Solde"))), h("tbody"));
    d.overdue_invoices.forEach(function (i) { od.tBodies[0].appendChild(h("tr", {}, h("td", {}, i.number), h("td", {}, i.client_name), h("td", {}, i.due_date), h("td", {class: "num"}, money(i.balance_cents)))); });
    v.appendChild(h("h5", {}, "Factures échues impayées")); v.appendChild(d.overdue_invoices.length ? od : h("p", {class: "text-muted"}, "Aucune."));
    v.appendChild(h("h5", {}, "Encaissements par mois"));
    var months = Object.keys(d.revenue_by_month_cents), max = Math.max.apply(null, months.map(function (m) { return d.revenue_by_month_cents[m]; }).concat([1]));
    months.forEach(function (m) {
      var bar = h("div", {class: "bar"}); bar.style.width = Math.max(2, Math.round(100 * d.revenue_by_month_cents[m] / max)) + "%";
      v.appendChild(h("div", {class: "row align-items-center mb-1"}, h("div", {class: "col-2"}, m), h("div", {class: "col-7"}, bar), h("div", {class: "col-3 num"}, money(d.revenue_by_month_cents[m]))));
    });
    if (!months.length) v.appendChild(h("p", {class: "text-muted"}, "Aucun encaissement."));
  }).catch(fail);
}

// ---- clients ---------------------------------------------------
function clientForm(c) {
  var f = h("form", {}, field("Nom", input("text", "name", c && c.name)), field("Type", select("kind", {particulier: "Particulier", entreprise: "Entreprise", avocat: "Cabinet / avocat", administration: "Administration"}, c && c.kind)),
    field("E-mail", input("email", "email", c && c.email)), field("Téléphone", input("text", "phone", c && c.phone)),
    field("Adresse", input("text", "address", c && c.address)), field("Identifiant fiscal (ICE / TVA)", input("text", "tax_id", c && c.tax_id)),
    field("Notes", input("text", "notes", c && c.notes)), h("button", {class: "btn btn-primary btn-sm", type: "submit"}, "Enregistrer"));
  f.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var body = {}; ["name", "kind", "email", "phone", "address", "tax_id", "notes"].forEach(function (k) { body[k] = val(f, k); });
    (c ? api("PUT", "/clients/" + c.id, body) : api("POST", "/clients", body)).then(function () { closeModal(); start(); }).catch(function (e) { f.appendChild(alertBox(e.message)); });
  });
  return f;
}
function viewClients() {
  var v = document.getElementById("view"); v.textContent = "";
  var q = input("search", "q"); q.placeholder = "Rechercher…";
  var add = h("button", {class: "btn btn-primary btn-sm", onclick: function () { openModal("Nouveau client", clientForm()); }}, "Nouveau client");
  var tbody = h("tbody");
  v.appendChild(h("div", {class: "d-flex gap-2 mb-3"}, q, add));
  v.appendChild(h("table", {class: "table table-sm table-hover"}, h("thead", {}, h("tr", {}, h("th", {}, "Nom"), h("th", {}, "Type"), h("th", {}, "E-mail"), h("th", {}, "Téléphone"), h("th"))), tbody));
  function load() {
    api("GET", "/clients?q=" + encodeURIComponent(q.value)).then(function (rows) {
      tbody.textContent = "";
      rows.forEach(function (c) {
        var actions = h("td", {class: "num"}, h("button", {class: "btn btn-outline-secondary btn-sm me-1", onclick: function () { openModal("Client", clientForm(c)); }}, "Modifier"));
        if (me.role === "admin") actions.appendChild(h("button", {class: "btn btn-outline-danger btn-sm", onclick: function () {
          if (confirm("Supprimer " + c.name + " ?")) api("DELETE", "/clients/" + c.id).then(load).catch(fail);
        }}, "Supprimer"));
        tbody.appendChild(h("tr", {}, h("td", {}, c.name), h("td", {}, c.kind), h("td", {}, c.email), h("td", {}, c.phone), actions));
      });
    }).catch(fail);
  }
  q.addEventListener("input", load); load();
}

// ---- cases -----------------------------------------------------
function viewCases() {
  var v = document.getElementById("view"); v.textContent = "";
  var filter = select("status", Object.assign({"": "Tous les statuts"}, STATUS), "");
  var tbody = h("tbody");
  v.appendChild(h("div", {class: "d-flex gap-2 mb-3"}, filter, h("button", {class: "btn btn-primary btn-sm", onclick: newCase}, "Nouveau dossier")));
  v.appendChild(h("table", {class: "table table-sm table-hover"}, h("thead", {}, h("tr", {}, ["Réf.", "Client", "Intitulé", "Langues", "Échéance", "Statut", "Travail du superagent"].map(function (t) { return h("th", {}, t); }))), tbody));
  function load() {
    api("GET", "/cases?status=" + encodeURIComponent(filter.value)).then(function (rows) {
      tbody.textContent = "";
      rows.forEach(function (c) {
        var st = select("status", STATUS, c.status);
        st.addEventListener("change", function () { api("PUT", "/cases/" + c.id, {status: st.value}).then(load).catch(fail); });
        tbody.appendChild(h("tr", {}, h("td", {}, c.ref), h("td", {}, c.client_name), h("td", {}, c.title), h("td", {}, c.src + " → " + c.tgt),
          h("td", {}, c.deadline), h("td", {}, st), h("td", {}, c.job_id || "—")));
      });
    }).catch(fail);
  }
  filter.addEventListener("change", load); load();
  function newCase() {
    api("GET", "/clients").then(function (cl) {
      var opts = {}; cl.forEach(function (c) { opts[c.id] = c.name; });
      if (!cl.length) { fail(new Error("Créez d'abord un client.")); return; }
      var f = h("form", {}, field("Client", select("client_id", opts)), field("Intitulé", input("text", "title")),
        field("Nature du document", input("text", "doc_kind")), field("Langue source", select("src", LANGS, "ar")), field("Langue cible", select("tgt", LANGS, "fr")),
        field("Échéance", input("date", "deadline")), field("Nombre de mots (estimation)", input("number", "words", "0")),
        field("Identifiant du travail superagent (facultatif)", input("text", "job_id")), h("button", {class: "btn btn-primary btn-sm", type: "submit"}, "Créer"));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        api("POST", "/cases", {client_id: parseInt(val(f, "client_id"), 10), title: val(f, "title"), doc_kind: val(f, "doc_kind"), src: val(f, "src"), tgt: val(f, "tgt"),
          deadline: val(f, "deadline"), words: parseInt(val(f, "words") || "0", 10), job_id: val(f, "job_id")}).then(function () { closeModal(); load(); }).catch(function (e) { f.appendChild(alertBox(e.message)); });
      });
      openModal("Nouveau dossier", f);
    }).catch(fail);
  }
}

// ---- quotes and invoices ---------------------------------------
function viewDocs() {
  var kind = tab, v = document.getElementById("view"); v.textContent = "";
  var tbody = h("tbody");
  v.appendChild(h("div", {class: "mb-3"}, h("button", {class: "btn btn-primary btn-sm", onclick: newDoc}, kind === "quote" ? "Nouveau devis" : "Nouvelle facture")));
  v.appendChild(h("table", {class: "table table-sm table-hover"}, h("thead", {}, h("tr", {}, ["Numéro", "Client", "Date", "Statut", "Total TTC", "Solde", ""].map(function (t, i) { return h("th", {class: i > 3 && i < 6 ? "num" : ""}, t); }))), tbody));
  function load() {
    api("GET", "/documents?kind=" + kind).then(function (rows) {
      tbody.textContent = "";
      rows.forEach(function (d) {
        var act = h("td", {class: "num"}, h("a", {class: "btn btn-outline-secondary btn-sm me-1", href: "/erp/print/" + d.id, target: "_blank", rel: "noopener"}, "Imprimer"));
        function btn(label, fn, cls) { act.appendChild(h("button", {class: "btn btn-sm me-1 " + (cls || "btn-outline-primary"), onclick: fn}, label)); }
        if (d.status === "draft") btn("Marquer envoyé", function () { api("POST", "/documents/" + d.id + "/status", {status: "sent"}).then(load).catch(fail); });
        if (kind === "quote" && (d.status === "sent" || d.status === "accepted")) btn("Facturer", function () { api("POST", "/documents/" + d.id + "/invoice", {}).then(function () { tab = "invoice"; start(); }).catch(fail); });
        if (kind === "invoice" && d.status === "sent") btn("Paiement", function () { payForm(d); });
        if (d.status !== "void" && d.status !== "paid") btn("Annuler", function () { if (confirm("Annuler " + d.number + " ?")) api("POST", "/documents/" + d.id + "/status", {status: "void"}).then(load).catch(fail); }, "btn-outline-danger");
        tbody.appendChild(h("tr", {}, h("td", {}, d.number), h("td", {}, d.client_name), h("td", {}, d.issue_date), h("td", {}, DOC_STATUS[d.status]),
          h("td", {class: "num"}, money(d.total_cents, d.currency)), h("td", {class: "num"}, kind === "invoice" ? money(d.balance_cents, d.currency) : "—"), act));
      });
    }).catch(fail);
  }
  load();
  function payForm(d) {
    var f = h("form", {}, h("p", {}, d.number + " · solde " + money(d.balance_cents, d.currency)), field("Montant", input("text", "amount", (d.balance_cents / 100).toFixed(2))),
      field("Date", input("date", "paid_on", new Date().toISOString().slice(0, 10))), field("Mode", select("method", {virement: "Virement", especes: "Espèces", cheque: "Chèque", carte: "Carte"})),
      field("Référence", input("text", "reference")), h("button", {class: "btn btn-primary btn-sm", type: "submit"}, "Enregistrer"));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      api("POST", "/documents/" + d.id + "/payments", {cents: toCents(val(f, "amount")), paid_on: val(f, "paid_on"), method: val(f, "method"), reference: val(f, "reference")})
        .then(function () { closeModal(); load(); }).catch(function (e) { f.appendChild(alertBox(e.message)); });
    });
    openModal("Paiement", f);
  }
  function newDoc() {
    api("GET", "/clients").then(function (cl) {
      if (!cl.length) { fail(new Error("Créez d'abord un client.")); return; }
      var opts = {}; cl.forEach(function (c) { opts[c.id] = c.name; });
      var lines = h("div"), f = h("form", {}, field("Client", select("client_id", opts)), field("Échéance (facultatif)", input("date", "due_date")),
        field("TVA (%)", input("text", "vat", "20")), field("Devise", input("text", "currency", "MAD")), lines);
      function addLine() {
        lines.appendChild(h("div", {class: "row g-1 mb-1 line"}, h("div", {class: "col-6"}, h("input", {class: "form-control form-control-sm", placeholder: "Désignation", name: "label"})),
          h("div", {class: "col-2"}, h("input", {class: "form-control form-control-sm", placeholder: "Qté", name: "qty", value: "1"})), h("div", {class: "col-4"}, h("input", {class: "form-control form-control-sm", placeholder: "Prix unitaire HT", name: "unit"}))));
      }
      addLine();
      f.appendChild(h("button", {class: "btn btn-outline-secondary btn-sm me-2", type: "button", onclick: addLine}, "+ ligne"));
      f.appendChild(h("button", {class: "btn btn-primary btn-sm", type: "submit"}, "Créer"));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var ls = [].slice.call(lines.querySelectorAll(".line")).map(function (r) {
          return {label: r.querySelector("[name=label]").value.trim(), qty_milli: Math.round(parseFloat(r.querySelector("[name=qty]").value.replace(",", ".")) * 1000), unit_cents: toCents(r.querySelector("[name=unit]").value)};
        }).filter(function (l) { return l.label; });
        api("POST", "/documents", {kind: kind, client_id: parseInt(val(f, "client_id"), 10), due_date: val(f, "due_date"), vat_permille: Math.round(parseFloat(val(f, "vat").replace(",", ".")) * 10),
          currency: val(f, "currency"), lines: ls}).then(function () { closeModal(); load(); }).catch(function (e) { f.appendChild(alertBox(e.message)); });
      });
      openModal(kind === "quote" ? "Nouveau devis" : "Nouvelle facture", f);
    }).catch(fail);
  }
}

document.getElementById("logout").addEventListener("click", function () { api("POST", "/logout", {}).then(showLogin).catch(showLogin); });
api("GET", "/me").then(function (j) { me = j; csrf = j.csrf; start(); }).catch(showLogin);
