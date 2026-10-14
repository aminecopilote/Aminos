"""Single-user web interface: streamlit run app.py   (multi-user: saas_app.py)"""
import streamlit as st

from aminos.webui import UiContext, render

st.set_page_config(page_title="Aminos", layout="wide")
st.title("Aminos — traduction juridique")
render(UiContext())
