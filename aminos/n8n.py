"""n8n automation for Aminos: builds the importable workflows and the credentials file.

`aminos n8n prepare` creates API tokens, writes `workflows/*.json` and a private `credentials.json`, ready for
`n8n import:credentials` / `n8n import:workflow`. Workflows only ever talk to the Aminos API with scoped tokens
(system: health/backup/jobs, read: dashboard, write: client and case intake). They cannot delete anything and they
cannot restart services; alerts go to a webhook URL you choose (Slack, Mattermost, Discord, ntfy...).
"""
from __future__ import annotations

import json
import os
import secrets
import uuid
from pathlib import Path

NS = uuid.UUID("6f1f3a64-0b53-4c35-9d47-3a0e0b6a8a11")
CRED_SYSTEM, CRED_READ, CRED_WRITE, CRED_INTAKE = ("Aminos token système", "Aminos token lecture", "Aminos token écriture",
                                                  "Aminos secret formulaire")
CRED_IDS = {n: str(uuid.uuid5(NS, n))[:16].replace("-", "") for n in (CRED_SYSTEM, CRED_READ, CRED_WRITE, CRED_INTAKE)}


def _id(workflow: str, name: str) -> str:
    return str(uuid.uuid5(NS, f"{workflow}/{name}"))


class Flow:
    """Tiny builder: nodes laid out left to right, linear connections plus explicit branches."""

    def __init__(self, name: str):
        self.name, self.nodes, self.conn, self._x = name, [], {}, 0

    def node(self, name: str, type_: str, params: dict, version: float = 1, cred: tuple[str, str] | None = None,
             y: int = 0, **extra) -> str:
        n = {"parameters": params, "id": _id(self.name, name), "name": name, "type": type_, "typeVersion": version,
             "position": [self._x, y]} | extra
        if cred:
            n["credentials"] = {cred[0]: {"id": CRED_IDS[cred[1]], "name": cred[1]}}
        self.nodes.append(n)
        self._x += 240
        return name

    def link(self, a: str, b: str, output: int = 0) -> None:
        outs = self.conn.setdefault(a, {"main": []})["main"]
        while len(outs) <= output:
            outs.append([])
        outs[output].append({"node": b, "type": "main", "index": 0})

    def chain(self, *names: str) -> None:
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def json(self) -> dict:
        return {"name": self.name, "nodes": self.nodes, "connections": self.conn, "active": False,
                "settings": {"executionOrder": "v1"}, "pinData": {}, "id": _id(self.name, "workflow")[:16].replace("-", ""),
                "versionId": _id(self.name, "version"), "meta": {"templateCredsSetupCompleted": False}, "tags": []}


def _set(values: dict[str, str]) -> dict:
    return {"assignments": {"assignments": [
        {"id": _id("set", k), "name": k, "value": v, "type": "string"} for k, v in values.items()]}, "options": {}}


def _http(method: str, url: str, **kw) -> dict:
    p: dict = {"method": method, "url": url, "options": {"timeout": kw.pop("timeout", 20000),
                                                          "response": {"response": {"neverError": True, "fullResponse": True}}}}
    p.update(kw)
    return p


def _auth(cred_name: str) -> dict:
    return {"authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}


def _alert_nodes(f: Flow, cond_name: str = "Faut-il alerter ?") -> tuple[str, str]:
    """IF alert -> POST the message to the webhook URL held in the Config node. Returns (if_node, post_node)."""
    cond = f.node(cond_name, "n8n-nodes-base.if", {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        "conditions": [
            {"id": _id(f.name, "c1"), "leftValue": "={{ $json.alert }}", "rightValue": True, "operator": {"type": "boolean", "operation": "true", "singleValue": True}},
            {"id": _id(f.name, "c2"), "leftValue": "={{ $('Config').item.json.alertUrl }}", "rightValue": "", "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}},
        ], "combinator": "and"}}, 2.2)
    post = f.node("Envoyer l'alerte", "n8n-nodes-base.httpRequest", _http(
        "POST", "={{ $('Config').item.json.alertUrl }}", sendBody=True, specifyBody="json",
        jsonBody="={{ JSON.stringify({ text: $json.message, content: $json.message, message: $json.message }) }}"), 4.2)
    f.link(cond, post, 0)
    return cond, post


CONFIG_DEFAULTS = {"erpUrl": "http://127.0.0.1:8502", "appUrl": "http://127.0.0.1:8501", "alertUrl": ""}


def health_monitor(cfg: dict) -> dict:
    f = Flow("Aminos · Surveillance des services")
    trig = f.node("Toutes les 5 minutes", "n8n-nodes-base.scheduleTrigger",
                  {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}}, 1.2)
    conf = f.node("Config", "n8n-nodes-base.set", _set({k: cfg[k] for k in ("erpUrl", "appUrl", "alertUrl")}), 3.4)
    f.link(f.node("Lancer à la main", "n8n-nodes-base.manualTrigger", {}, 1, y=-140), conf)
    http = f.node("État du système", "n8n-nodes-base.httpRequest",
                  _http("GET", "={{ $json.erpUrl }}/erp/api/system/status", **_auth(CRED_SYSTEM)), 4.2, ("httpHeaderAuth", CRED_SYSTEM))
    code = f.node("Évaluer", "n8n-nodes-base.code", {"jsCode": """
// Alert on a change of state, and remind every 60 minutes while something is wrong.
const res = $input.first().json;
const state = $getWorkflowStaticData('global');
let problems = [];
if (res.statusCode !== 200) problems.push('back-office injoignable ou jeton refusé (HTTP ' + res.statusCode + ')');
else problems = (res.body && res.body.problems) || [];
const ok = problems.length === 0, now = Date.now();
let alert = false, message = '';
if (!ok && (state.ok !== false || now - (state.lastAlert || 0) > 3600000)) {
  alert = true; message = '⚠️ Aminos : ' + problems.join(' ; ');
} else if (ok && state.ok === false) {
  alert = true; message = '✅ Aminos : rétabli';
}
if (alert) state.lastAlert = now;
state.ok = ok;
return [{ json: { alert, ok, message, problems } }];
"""}, 2)
    f.chain(trig, conf, http, code)
    _alert_nodes(f)
    f.link(code, "Faut-il alerter ?")
    return f.json()


def daily_digest(cfg: dict) -> dict:
    f = Flow("Aminos · Récapitulatif quotidien (retards, factures échues)")
    trig = f.node("Chaque jour à 8 h", "n8n-nodes-base.scheduleTrigger",
                  {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * *"}]}}, 1.2)
    conf = f.node("Config", "n8n-nodes-base.set", _set({k: cfg[k] for k in ("erpUrl", "alertUrl")}), 3.4)
    f.link(f.node("Lancer à la main", "n8n-nodes-base.manualTrigger", {}, 1, y=-140), conf)
    http = f.node("Tableau de bord", "n8n-nodes-base.httpRequest",
                  _http("GET", "={{ $json.erpUrl }}/erp/api/dashboard", **_auth(CRED_READ)), 4.2, ("httpHeaderAuth", CRED_READ))
    code = f.node("Composer le message", "n8n-nodes-base.code", {"jsCode": """
const r = $input.first().json;
if (r.statusCode !== 200) return [{ json: { alert: true, message: '⚠️ Récapitulatif impossible : HTTP ' + r.statusCode } }];
const d = r.body, lines = [];
for (const c of d.late_cases) lines.push('• dossier en retard ' + c.ref + ' (' + c.client_name + ') échéance ' + c.deadline);
for (const i of d.overdue_invoices) lines.push('• facture échue ' + i.number + ' (' + i.client_name + ') solde ' + (i.balance_cents / 100).toFixed(2));
const msg = lines.length ? 'Aminos, récapitulatif du jour :\\n' + lines.join('\\n') + '\\nEncours à recevoir : ' + (d.outstanding_cents / 100).toFixed(2) : '';
return [{ json: { alert: lines.length > 0, message: msg } }];
"""}, 2)
    f.chain(trig, conf, http, code)
    _alert_nodes(f)
    f.link(code, "Faut-il alerter ?")
    return f.json()


def nightly_backup(cfg: dict) -> dict:
    f = Flow("Aminos · Sauvegarde nocturne")
    trig = f.node("Chaque nuit à 2 h 30", "n8n-nodes-base.scheduleTrigger",
                  {"rule": {"interval": [{"field": "cronExpression", "expression": "30 2 * * *"}]}}, 1.2)
    conf = f.node("Config", "n8n-nodes-base.set", _set({k: cfg[k] for k in ("erpUrl", "alertUrl")}), 3.4)
    f.link(f.node("Lancer à la main", "n8n-nodes-base.manualTrigger", {}, 1, y=-140), conf)
    http = f.node("Lancer la sauvegarde", "n8n-nodes-base.httpRequest",
                  _http("POST", "={{ $json.erpUrl }}/erp/api/system/backup", timeout=600000, **_auth(CRED_SYSTEM)), 4.2,
                  ("httpHeaderAuth", CRED_SYSTEM))
    code = f.node("Vérifier", "n8n-nodes-base.code", {"jsCode": """
const r = $input.first().json;
const ok = r.statusCode === 200 && r.body && r.body.ok === true;
return [{ json: { alert: !ok, message: ok ? '' : '⚠️ Aminos : la sauvegarde nocturne a échoué (HTTP ' + r.statusCode + ' ' + JSON.stringify((r.body && r.body.files || []).filter(f => !f.integrity_ok)) + ')' } }];
"""}, 2)
    f.chain(trig, conf, http, code)
    _alert_nodes(f)
    f.link(code, "Faut-il alerter ?")
    return f.json()


def jobs_watch(cfg: dict) -> dict:
    f = Flow("Aminos · Dossiers du superagent non concluants")
    trig = f.node("Toutes les 15 minutes", "n8n-nodes-base.scheduleTrigger",
                  {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}}, 1.2)
    conf = f.node("Config", "n8n-nodes-base.set", _set({k: cfg[k] for k in ("erpUrl", "alertUrl")}), 3.4)
    f.link(f.node("Lancer à la main", "n8n-nodes-base.manualTrigger", {}, 1, y=-140), conf)
    http = f.node("Dossiers du superagent", "n8n-nodes-base.httpRequest",
                  _http("GET", "={{ $json.erpUrl }}/erp/api/system/jobs", **_auth(CRED_SYSTEM)), 4.2, ("httpHeaderAuth", CRED_SYSTEM))
    code = f.node("Nouveaux non concluants", "n8n-nodes-base.code", {"jsCode": """
const r = $input.first().json;
if (r.statusCode !== 200) return [{ json: { alert: false } }];
const seen = $getWorkflowStaticData('global');
seen.notified = seen.notified || {};
const fresh = (r.body || []).filter(j => j.status === 'non_concluant' && !seen.notified[j.org + '/' + j.id]);
fresh.forEach(j => seen.notified[j.org + '/' + j.id] = Date.now());
const msg = fresh.map(j => '• ' + j.org + ' : ' + j.id + ' (' + j.issues + ' point(s) à traiter)').join('\\n');
return [{ json: { alert: fresh.length > 0, message: fresh.length ? 'Aminos : dossier(s) de traduction non concluant(s), relecture nécessaire :\\n' + msg : '' } }];
"""}, 2)
    f.chain(trig, conf, http, code)
    _alert_nodes(f)
    f.link(code, "Faut-il alerter ?")
    return f.json()


def client_intake(cfg: dict) -> dict:
    """Public form -> client + case in the back-office. The webhook itself demands a secret header."""
    f = Flow("Aminos · Demande de traduction (formulaire web → client + dossier)")
    hook = f.node("Formulaire (POST /webhook/aminos-demande)", "n8n-nodes-base.webhook", {
        "httpMethod": "POST", "path": "aminos-demande", "authentication": "headerAuth", "responseMode": "responseNode",
        "options": {}}, 2, ("httpHeaderAuth", CRED_INTAKE), webhookId=_id(f.name, "hook"))
    conf = f.node("Config", "n8n-nodes-base.set", _set({"erpUrl": cfg["erpUrl"]}), 3.4)
    check = f.node("Valider", "n8n-nodes-base.code", {"jsCode": """
const b = $('Formulaire (POST /webhook/aminos-demande)').first().json.body || {};
const langs = ['ar', 'fr', 'en', 'nl'];
const str = (v, n) => (typeof v === 'string' ? v.trim().slice(0, n) : '');
const out = { name: str(b.name, 200), email: str(b.email, 200), phone: str(b.phone, 60), title: str(b.title, 200),
  doc_kind: str(b.doc_kind, 100), src: str(b.src, 8).toLowerCase(), tgt: str(b.tgt, 8).toLowerCase(), deadline: str(b.deadline, 10) };
const errors = [];
if (!out.name) errors.push('name');
if (!out.title) errors.push('title');
if (!langs.includes(out.src) || !langs.includes(out.tgt) || out.src === out.tgt) errors.push('src/tgt');
if (out.deadline && !/^\\d{4}-\\d{2}-\\d{2}$/.test(out.deadline)) errors.push('deadline');
return [{ json: { valid: errors.length === 0, errors, data: out, erpUrl: $('Config').first().json.erpUrl } }];
"""}, 2)
    ok = f.node("Données valides ?", "n8n-nodes-base.if", {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        "conditions": [{"id": _id(f.name, "v"), "leftValue": "={{ $json.valid }}", "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}], "combinator": "and"}}, 2.2, y=0)
    client = f.node("Créer le client", "n8n-nodes-base.httpRequest", _http(
        "POST", "={{ $json.erpUrl }}/erp/api/clients", sendBody=True, specifyBody="json",
        jsonBody="={{ JSON.stringify({ name: $json.data.name, email: $json.data.email, phone: $json.data.phone, notes: 'Demande reçue par le formulaire web' }) }}",
        **_auth(CRED_WRITE)), 4.2, ("httpHeaderAuth", CRED_WRITE), y=-100)
    case = f.node("Créer le dossier", "n8n-nodes-base.httpRequest", _http(
        "POST", "={{ $('Valider').first().json.erpUrl }}/erp/api/cases", sendBody=True, specifyBody="json",
        jsonBody="={{ JSON.stringify({ client_id: $json.body.id, title: $('Valider').first().json.data.title, doc_kind: $('Valider').first().json.data.doc_kind, src: $('Valider').first().json.data.src, tgt: $('Valider').first().json.data.tgt, deadline: $('Valider').first().json.data.deadline }) }}",
        **_auth(CRED_WRITE)), 4.2, ("httpHeaderAuth", CRED_WRITE), y=-100)
    done = f.node("Répondre : reçu", "n8n-nodes-base.respondToWebhook", {
        "respondWith": "json", "responseBody": "={{ JSON.stringify($json.statusCode === 201 ? { ok: true, reference: $json.body.ref } : { ok: false, error: 'enregistrement impossible' }) }}",
        "options": {"responseCode": "={{ $json.statusCode === 201 ? 201 : 502 }}"}}, 1.1, y=-100)
    bad = f.node("Répondre : données invalides", "n8n-nodes-base.respondToWebhook", {
        "respondWith": "json", "responseBody": "={{ JSON.stringify({ ok: false, errors: $json.errors }) }}",
        "options": {"responseCode": 400}}, 1.1, y=100)
    f.chain(hook, conf, check, ok)
    f.link(ok, client, 0)
    f.link(ok, bad, 1)
    f.chain(client, case, done)
    return f.json()


BUILDERS = {"aminos-surveillance.json": health_monitor, "aminos-recapitulatif.json": daily_digest,
            "aminos-sauvegarde.json": nightly_backup, "aminos-dossiers-non-concluants.json": jobs_watch,
            "aminos-formulaire-demande.json": client_intake}


def write_workflows(out_dir: str | Path, erp_url: str, app_url: str, alert_url: str = "") -> list[Path]:
    cfg = CONFIG_DEFAULTS | {"erpUrl": erp_url.rstrip("/"), "appUrl": app_url.rstrip("/"), "alertUrl": alert_url}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, build in BUILDERS.items():
        p = out / name
        p.write_text(json.dumps(build(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
        paths.append(p)
    return paths


def credentials(system: str, read: str, write: str, intake_secret: str) -> list[dict]:
    """Header-auth credentials in the shape of `n8n import:credentials` (plain data, n8n encrypts it on import)."""
    def hdr(name, header, value):
        return {"id": CRED_IDS[name], "name": name, "type": "httpHeaderAuth", "data": {"name": header, "value": value}}
    return [hdr(CRED_SYSTEM, "Authorization", f"Bearer {system}"), hdr(CRED_READ, "Authorization", f"Bearer {read}"),
            hdr(CRED_WRITE, "Authorization", f"Bearer {write}"), hdr(CRED_INTAKE, "X-Aminos-Secret", intake_secret)]


def prepare(out_dir: str | Path, data_dir: str | Path, org: str, erp_url: str, app_url: str, alert_url: str = "") -> dict:
    """Create the tokens and write everything n8n needs into out_dir. Existing credentials.json is kept (tokens stay valid)."""
    from .erp.tokens import TokenStore
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cred_path = out / "credentials.json"
    secret = None
    if cred_path.exists():
        creds = json.loads(cred_path.read_text(encoding="utf-8"))
        secret = next(c["data"]["value"] for c in creds if c["name"] == CRED_INTAKE)
    else:
        ts = TokenStore(data_dir)
        secret = secrets.token_urlsafe(24)
        creds = credentials(ts.create("system", label="n8n"), ts.create("read", org, "n8n"), ts.create("write", org, "n8n"), secret)
        fd = os.open(cred_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(creds, fh, indent=2)
    paths = write_workflows(out / "workflows", erp_url, app_url, alert_url)
    return {"credentials": str(cred_path), "workflows": [str(p) for p in paths], "intake_secret": secret}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="aminos n8n")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="créer les jetons et écrire workflows + credentials.json pour n8n")
    p.add_argument("--out", required=True, help="dossier de sortie (credentials.json y est en mode 0600)")
    p.add_argument("--data", default=os.environ.get("AMINOS_DATA_DIR", "saas-data"))
    p.add_argument("--org", default="admin", help="cabinet auquel sont liés les jetons lecture/écriture")
    p.add_argument("--erp-url", default="http://127.0.0.1:8502")
    p.add_argument("--app-url", default="http://127.0.0.1:8501")
    p.add_argument("--alert-url", default="", help="webhook d'alerte (Slack, Mattermost, Discord, ntfy…) ; modifiable dans n8n")
    a = ap.parse_args(argv)
    r = prepare(a.out, a.data, a.org, a.erp_url, a.app_url, a.alert_url)
    print(f"credentials : {r['credentials']}  (secret : ne pas partager)")
    for w in r["workflows"]:
        print("workflow    :", w)
    print(f"secret du formulaire (en-tête X-Aminos-Secret) : {r['intake_secret']}")
    return 0
