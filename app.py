"""Single-user web interface: streamlit run app.py   (multi-user: saas_app.py)"""
import streamlit as st

import os

from aminos.superagent.ui import render_superagent
from aminos.webui import UiContext, render

st.set_page_config(page_title="Aminos", layout="wide")
st.title("Aminos — traduction juridique")
ctx = UiContext()
t1, t2 = st.tabs(["Traduction", "Superagent"])
with t1:
    render(ctx)
with t2:
    render_superagent(os.environ.get("AMINOS_PROFILE_DIR", "superagent-profile"), os.environ.get("AMINOS_WORK_DIR", "superagent-work"),
                      ctx.providers, ctx.default_provider, True, ctx.tm_path)
