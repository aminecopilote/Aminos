"""End-to-end check of the n8n workflows against a real n8n (not collected by unittest).

  N8N_BIN=/path/to/n8n python tests/n8n_e2e.py
Starts the back-office and a fake alert receiver, imports credentials + workflows with the real n8n CLI, runs the four
scheduled workflows once, publishes the intake webhook and posts a form to it.
"""
import http.server
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from aminos.n8n import prepare

N8N = os.environ.get("N8N_BIN", "n8n")
tmp = Path(tempfile.mkdtemp())
data, home = tmp / "data", tmp / "n8nhome"
env = {**os.environ, "N8N_USER_FOLDER": str(home), "N8N_DIAGNOSTICS_ENABLED": "false", "N8N_PORT": "5678",
       "N8N_LISTEN_ADDRESS": "127.0.0.1", "N8N_SECURE_COOKIE": "false", "N8N_VERSION_NOTIFICATIONS_ENABLED": "false"}
alerts: list[dict] = []


class Alert(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        alerts.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def n8n(*args, check=True):
    r = subprocess.run([N8N, *args], env=env, capture_output=True, text=True, timeout=300)
    if check and r.returncode != 0:
        sys.exit(f"n8n {' '.join(args)} failed:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def fail(msg):
    print("FAIL:", msg)
    cleanup()
    sys.exit(1)


procs = []


def cleanup():
    for p in procs:
        p.terminate()
    time.sleep(1)
    shutil.rmtree(tmp, ignore_errors=True)


srv = http.server.HTTPServer(("127.0.0.1", 0), Alert)
threading.Thread(target=srv.serve_forever, daemon=True).start()
alert_url = f"http://127.0.0.1:{srv.server_port}/alert"
erp_port = 18502

res = prepare(tmp / "setup", data, "admin", f"http://127.0.0.1:{erp_port}", "http://127.0.0.1:1", alert_url)
procs.append(subprocess.Popen([sys.executable, "-m", "aminos.erp", "--data", str(data), "--port", str(erp_port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
for _ in range(30):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{erp_port}/erp/", timeout=2)
        break
    except Exception:
        time.sleep(1)
else:
    fail("back-office did not start")

n8n("import:credentials", f"--input={res['credentials']}")
n8n("import:workflow", "--separate", f"--input={Path(res['credentials']).parent / 'workflows'}")
ids = {}
for line in n8n("list:workflow").stdout.splitlines():
    if "|" in line:
        i, name = line.split("|", 1)
        ids[name.strip()] = i.strip()
if len(ids) != 5:
    fail(f"expected 5 workflows, got {ids}")
by = lambda key: next(i for n, i in ids.items() if key in n)

# a job the superagent could not conclude, so the watcher has something to report
job = data / "tenants" / "admin" / "work" / "jobs" / "acte-1"
job.mkdir(parents=True)
(job / "job.json").write_text(json.dumps({"id": "acte-1", "status": "non_concluant", "issues": ["a"], "updated": 1}))

for key in ("Surveillance", "non concluants", "Sauvegarde", "Récapitulatif"):
    out = n8n("execute", f"--id={by(key)}").stdout
    if '"status": "success"' not in out:
        fail(f"workflow {key} did not succeed:\n{out[-1500:]}")
    print("executed:", key)
if not any("non concluant" in a.get("text", "") for a in alerts):
    fail(f"no alert for the inconclusive job: {alerts}")
backups = list((data / "backups").glob("*/manifest.json"))
if not backups or not json.loads(backups[0].read_text())["ok"]:
    fail("nightly backup did not produce a consistent backup")
print("alerts received:", len(alerts), "| backup ok")

for i in ids.values():
    n8n("publish:workflow", f"--id={i}")
procs.append(subprocess.Popen([N8N, "start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
secret = res["intake_secret"]


def post(body, secret_value):
    req = urllib.request.Request("http://127.0.0.1:5678/webhook/aminos-demande", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-Aminos-Secret": secret_value})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except urllib.error.URLError:            # n8n is not listening yet
        return 0, ""


form = {"name": "Fatima ALAMI", "email": "f@example.org", "title": "Acte de naissance", "doc_kind": "état civil",
        "src": "ar", "tgt": "fr", "deadline": "2030-12-01"}
for _ in range(60):                      # n8n activates published workflows a few seconds after it answers /healthz
    status, body = post(form, secret)
    if status not in (0, 404):
        break
    time.sleep(2)
if status != 201 or not json.loads(body).get("ok"):
    fail(f"intake webhook: {status} {body}")
if post(form, "wrong")[0] != 403:
    fail("webhook accepted a wrong secret")
if post({**form, "src": "fr", "tgt": "fr"}, secret)[0] != 400:
    fail("invalid languages accepted")
db = sqlite3.connect(data / "tenants" / "admin" / "erp.sqlite")
if db.execute("SELECT COUNT(*) FROM clients").fetchone()[0] != 1 or db.execute("SELECT COUNT(*) FROM cases").fetchone()[0] != 1:
    fail("form did not create exactly one client and one case")
print("N8N E2E OK")
cleanup()
