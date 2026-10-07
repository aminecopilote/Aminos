"""Web interface: streamlit run app.py"""
import os
import tempfile
from pathlib import Path

import streamlit as st

from aminos import checks
from aminos.docx_out import build_docx
from aminos.extract import extract_paragraphs, ocr_claude, ocr_tesseract
from aminos.glossary import Glossary, import_file
from aminos.providers import PROVIDERS, build_chat
from aminos.pipeline import translate_document
from aminos.tm import TranslationMemory

st.set_page_config(page_title="Aminos", layout="wide")
st.title("Aminos — traduction juridique")

with st.sidebar:
    key = st.text_input("Clé ANTHROPIC_API_KEY", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""))
    src = st.selectbox("Langue source", ["arabe", "français", "anglais"])
    tgt = st.selectbox("Langue cible", ["français", "arabe", "anglais"], index=0)
    provider = st.multiselect("Fournisseur(s) LLM (ordre = repli)", ["anthropic", *PROVIDERS], default=["anthropic"])
    allow_free = st.checkbox("J'accepte l'envoi du texte à un tiers (document NON confidentiel)")
    mode = st.radio("Mode", ["fast", "normal", "hard"], index=1)
    ocr_kind = st.selectbox("OCR (scans, images)", ["aucun", "claude", "tesseract"])
    juris = st.text_input("Juridiction", "")
    tm_path = st.text_input("Base de mémoire de traduction", "tm.sqlite")
    gloss_files = st.file_uploader("Glossaires", accept_multiple_files=True,
                                   type=["csv", "tsv", "txt", "json", "xlsx", "docx", "pdf"])

upload = st.file_uploader("Document à traduire", type=["docx", "pdf", "txt", "png", "jpg", "jpeg", "webp"])

if upload and st.button("Traduire", type="primary"):
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    with tempfile.TemporaryDirectory() as d:
        gloss = Glossary()
        for f in gloss_files:
            fp = Path(d) / f.name
            fp.write_bytes(f.getvalue())
            gloss.extend(import_file(fp))
        fp = Path(d) / upload.name
        fp.write_bytes(upload.getvalue())
        ocr = {"claude": ocr_claude, "tesseract": ocr_tesseract}.get(ocr_kind, lambda: None)()
        with st.spinner("Extraction…"):
            paragraphs = extract_paragraphs(fp, ocr)
        with st.spinner("Traduction…"):
            out = translate_document(build_chat(",".join(provider) or "anthropic", None, allow_free), paragraphs, src, tgt, gloss, mode, juris,
                                     tm=TranslationMemory(tm_path))
        out_path = Path(d) / f"{Path(upload.name).stem}_{tgt}.docx"
        build_docx(out, tgt, str(out_path))
        st.session_state["docx"] = (out_path.name, out_path.read_bytes())
        st.session_state["pairs"] = list(zip(paragraphs, out))
        st.session_state["issues"] = [m for s_, t_ in st.session_state["pairs"]
                                      for m in checks.compare(s_, t_).issues()] + [
            f"« {t.source} » doit être « {t.target} »" for s_, t_ in st.session_state["pairs"]
            for t in gloss.missing_in(s_, t_)]

if "docx" in st.session_state:
    name, data = st.session_state["docx"]
    st.download_button("Télécharger le .docx", data, name)
    for issue in st.session_state["issues"]:
        st.warning(issue)
    if not st.session_state["issues"]:
        st.success("Contrôles terminologie et nombres : RAS")
    for s_, t_ in st.session_state["pairs"]:
        c1, c2 = st.columns(2)
        c1.markdown(s_)
        c2.markdown(t_)
