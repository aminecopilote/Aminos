"""Browser test of the back-office (not collected by unittest: needs Playwright + Chromium).

  python tests/ui_erp.py http://127.0.0.1:8502 <admin password> [screenshot.png]
Drives the real UI: sign in, create a client, a case, a quote, bill it, take the payment, read the dashboard, and checks
that HTML typed into a field is displayed as text and that no script or resource from another host is loaded.
"""
import os
import sys

from playwright.sync_api import sync_playwright

base, password = sys.argv[1].rstrip("/"), sys.argv[2]
shot = sys.argv[3] if len(sys.argv) > 3 else ""
errors, foreign = [], []
with sync_playwright() as p:
    exe = os.environ.get("PW_CHROMIUM")
    b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("request", lambda r: foreign.append(r.url) if not r.url.startswith(base) and not r.url.startswith("data:") else None)
    pg.goto(base + "/erp/")
    pg.fill("input[name=username]", "admin")
    pg.fill("input[name=password]", password)
    pg.click("button[type=submit]")
    pg.wait_for_selector("text=Tableau de bord")
    pg.click("a:has-text('Clients')")
    pg.click("button:has-text('Nouveau client')")
    pg.fill("#modal-body input[name=name]", "Cabinet <b>Alami</b>")
    pg.click("#modal-body button[type=submit]")
    pg.wait_for_selector("td:has-text('Cabinet <b>Alami</b>')")
    pg.click("a:has-text('Dossiers')")
    pg.click("button:has-text('Nouveau dossier')")
    pg.fill("#modal-body input[name=title]", "Acte de mariage")
    pg.fill("#modal-body input[name=deadline]", "2020-01-01")
    pg.click("#modal-body button[type=submit]")
    pg.wait_for_selector("td:has-text('Acte de mariage')")
    pg.click("a:has-text('Devis')")
    pg.click("button:has-text('Nouveau devis')")
    pg.fill("#modal-body input[name=label]", "Traduction")
    pg.fill("#modal-body input[name=qty]", "2")
    pg.fill("#modal-body input[name=unit]", "150")
    pg.click("#modal-body button[type=submit]")
    pg.wait_for_selector("td:has-text('DV-')")
    pg.click("button:has-text('Marquer envoyé')")
    pg.wait_for_selector("button:has-text('Facturer')")
    pg.click("button:has-text('Facturer')")
    pg.wait_for_selector("td:has-text('FA-')")
    pg.click("button:has-text('Marquer envoyé')")
    pg.wait_for_selector("button:has-text('Paiement')")
    pg.click("button:has-text('Paiement')")
    pg.click("#modal-body button[type=submit]")
    pg.wait_for_selector("td:has-text('Payé')")
    total = pg.inner_text("tbody tr td:nth-child(5)")
    assert "360,00" in total.replace("\u202f", " ").replace("\xa0", " "), total      # 2 x 150 + 20 % VAT
    pg.click("a:has-text('Tableau de bord')")
    pg.wait_for_selector("text=Encaissements par mois")
    assert pg.locator("#view b").count() == 0, "HTML typed by a user was interpreted"
    if shot:
        pg.screenshot(path=shot, full_page=True)
    b.close()
assert not errors, errors
assert not foreign, f"requests to other hosts: {foreign}"
print("ERP UI OK")
