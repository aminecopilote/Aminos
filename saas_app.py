"""Multi-user web interface: streamlit run saas_app.py

Configuration (environment):
  AMINOS_DATA_DIR            where accounts, memories and audit logs live (default ./saas-data)
  AMINOS_ADMIN_USER / AMINOS_ADMIN_PASSWORD   creates the first administrator when no account exists
  AMINOS_SESSION_MINUTES     idle time before logging out (default 60)
  AMINOS_ALLOW_REMOTE_LLM    1 to let administrators grant accounts the right to use third-party model providers
"""
import os
import time

import streamlit as st

from aminos.providers import PROVIDERS
from aminos.saas import AuthError, QuotaExceeded, SaaSStore
from aminos.saas.store import new_password
from aminos.webui import UiContext, render

st.set_page_config(page_title="Aminos", layout="wide")


@st.cache_resource
def store() -> SaaSStore:
    s = SaaSStore(os.environ.get("AMINOS_DATA_DIR", "saas-data"))
    s.bootstrap_admin(os.environ.get("AMINOS_ADMIN_USER"), os.environ.get("AMINOS_ADMIN_PASSWORD"))
    return s


S = store()
IDLE = int(os.environ.get("AMINOS_SESSION_MINUTES", "60")) * 60
REMOTE_POSSIBLE = os.environ.get("AMINOS_ALLOW_REMOTE_LLM") == "1"


def logout(reason: str = "") -> None:
    st.session_state.clear()
    if reason:
        st.session_state["notice"] = reason


def login_screen() -> None:
    st.title("Aminos — traduction juridique")
    if S.count_users() == 0:
        st.error("Aucun compte. L'administrateur doit définir AMINOS_ADMIN_USER et AMINOS_ADMIN_PASSWORD au premier démarrage.")
        return
    if st.session_state.get("notice"):
        st.info(st.session_state.pop("notice"))
    with st.form("login"):
        u = st.text_input("Identifiant")
        p = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter", type="primary"):
            try:
                user = S.authenticate(u, p)
            except AuthError as e:
                st.error(str(e))
            else:
                st.session_state.update(user=user.username, last=time.time())
                S.audit(user, "login")
                st.rerun()


def admin_tab(me) -> None:
    st.subheader("Comptes")
    for u in S.list_users():
        docs, chars = S.usage_today(u.username)
        st.write(f"**{u.username}** · cabinet `{u.org}` · {u.role} · {'actif' if u.active else 'désactivé'} · "
                 f"aujourd'hui {docs}/{u.quota_docs_day} documents, {chars}/{u.quota_chars_day} caractères"
                 f"{' · fournisseurs distants autorisés' if u.allow_remote_llm else ''}")
    with st.expander("Créer un compte"):
        with st.form("create"):
            c1, c2, c3 = st.columns(3)
            name, org = c1.text_input("Identifiant"), c2.text_input("Cabinet (ex. cabinet-alami)")
            role = c3.selectbox("Rôle", ["user", "admin"])
            qd, qc = st.number_input("Documents par jour", 1, 100000, 20), st.number_input("Caractères par jour", 1000, 10**8, 400000)
            remote = st.checkbox("Autoriser les fournisseurs distants (texte envoyé à un tiers)", disabled=not REMOTE_POSSIBLE)
            if st.form_submit_button("Créer"):
                pw = new_password()
                try:
                    S.create_user(name, pw, org, role, quota_docs_day=int(qd), quota_chars_day=int(qc), allow_remote_llm=remote)
                    S.audit(me, "create_user", detail=name)
                    st.success(f"Compte créé. Mot de passe provisoire (affiché une seule fois) : `{pw}`")
                except AuthError as e:
                    st.error(str(e))
    with st.expander("Modifier un compte"):
        with st.form("edit"):
            target = st.selectbox("Compte", [u.username for u in S.list_users()])
            active = st.checkbox("Actif", value=True)
            reset = st.checkbox("Réinitialiser le mot de passe")
            if st.form_submit_button("Appliquer"):
                if target == me.username and not active:
                    st.error("Vous ne pouvez pas désactiver votre propre compte.")
                else:
                    S.update_user(target, active=active)
                    msg = "Compte mis à jour."
                    if reset:
                        pw = new_password()
                        S.set_password(target, pw)
                        msg += f" Nouveau mot de passe provisoire : `{pw}`"
                    S.audit(me, "edit_user", detail=target)
                    st.success(msg)
    st.subheader("Journal d'audit")
    orgs = sorted({u.org for u in S.list_users()})
    org = st.selectbox("Cabinet", orgs)
    ledger = S.audit_ledger(org)
    try:
        st.success(f"Chaîne intacte : {ledger.verify()} entrée(s).")
    except Exception as e:
        st.error(f"Journal altéré : {e}")
    for e in reversed(ledger.entries()[-50:]):
        st.text(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(e['ts']))} UTC  {e['extra'].get('user', ''):12} {e['label']}  {e['extra'].get('detail', '')}")


def main() -> None:
    username = st.session_state.get("user")
    if username and time.time() - st.session_state.get("last", 0) > IDLE:
        logout("Session expirée, reconnectez-vous.")
        username = None
    user = S.get(username) if username else None
    if not user or not user.active:
        if username:
            logout("Compte désactivé ou introuvable.")
        login_screen()
        return
    st.session_state["last"] = time.time()

    with st.sidebar:
        st.caption(f"{user.username} · {user.org}")
        if st.button("Se déconnecter"):
            S.audit(user, "logout")
            logout()
            st.rerun()

    remote = REMOTE_POSSIBLE and user.allow_remote_llm
    ctx = UiContext(
        multi_user=True, tm_path=S.tm_path(user), remote_allowed=remote,
        providers=["ollama", *(["anthropic", *[p for p in PROVIDERS if p != "ollama"]] if remote else [])],
        default_provider="ollama", ocr_options=["aucun", "tesseract", *(["claude"] if remote else [])],
        before_translate=lambda chars, name: S.consume(user, chars),
        after_translate=lambda digest, name: S.audit(user, "translate", digest, name))

    st.title("Aminos — traduction juridique")
    if user.is_admin:
        t1, t2 = st.tabs(["Traduction", "Administration"])
        with t1:
            render(ctx)
        with t2:
            admin_tab(user)
    else:
        render(ctx)
        docs, chars = S.usage_today(user.username)
        st.sidebar.caption(f"Aujourd'hui : {docs}/{user.quota_docs_day} documents")


main()
