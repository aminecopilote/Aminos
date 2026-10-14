"""Streamlit translation page, shared by the single-user app (app.py) and the multi-user app (saas_app.py).

In multi-user mode the caller passes a locked-down UiContext: the translation-memory path is fixed (a user must never
choose a path), the API key is never taken from the page into the process environment (it would leak to other
users), and only the providers the account may use are offered.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import streamlit as st

from . import checks
from .docx_out import build_docx
from .extract import extract_paragraphs, ocr_claude, ocr_tesseract
from .glossary import Glossary, import_file
from .pipeline import translate_document
from .providers import PROVIDERS, build_chat
from .tm import TranslationMemory


@dataclass
class UiContext:
    multi_user: bool = False
    tm_path: str = "tm.sqlite"
    providers: list[str] = field(default_factory=lambda: ["anthropic", *PROVIDERS])
    default_provider: str = "anthropic"
    ocr_options: list[str] = field(default_factory=lambda: ["aucun", "claude", "tesseract"])
    remote_allowed: bool = True
    # called before work starts (may raise to refuse, e.g. quota) and after the document is produced
    before_translate: Callable[[int, str], None] | None = None
    after_translate: Callable[[str, str], None] | None = None


def render(ctx: UiContext) -> None:
    with st.sidebar:
        key = ""
        if not ctx.multi_user:
            key = st.text_input("Clé ANTHROPIC_API_KEY", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""))
        src = st.selectbox("Langue source", ["arabe", "français", "anglais", "néerlandais"])
        tgt = st.selectbox("Langue cible", ["français", "arabe", "anglais", "néerlandais"], index=0)
        provider = st.multiselect("Fournisseur(s) LLM (ordre = repli)", ctx.providers,
                                  default=[ctx.default_provider] if ctx.default_provider in ctx.providers else [])
        allow_free = False
        if ctx.remote_allowed:
            allow_free = st.checkbox("J'accepte l'envoi du texte à un tiers (document NON confidentiel)")
        mode = st.radio("Mode", ["fast", "normal", "hard"], index=1)
        ocr_kind = st.selectbox("OCR (scans, images)", ctx.ocr_options)
        juris = st.text_input("Juridiction", "")
        tm_path = ctx.tm_path if ctx.multi_user else st.text_input("Base de mémoire de traduction", ctx.tm_path)
        gloss_files = st.file_uploader("Glossaires", accept_multiple_files=True,
                                       type=["csv", "tsv", "txt", "json", "xlsx", "docx", "pdf"])

    upload = st.file_uploader("Document à traduire", type=["docx", "pdf", "txt", "png", "jpg", "jpeg", "webp"])

    if upload and st.button("Traduire", type="primary"):
        if not provider:
            st.error("Choisissez au moins un fournisseur.")
        else:
            _translate(ctx, upload, gloss_files, key, src, tgt, provider, allow_free, mode, ocr_kind, juris, tm_path)

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


def _translate(ctx, upload, gloss_files, key, src, tgt, provider, allow_free, mode, ocr_kind, juris, tm_path) -> None:
    if key and not ctx.multi_user:
        os.environ["ANTHROPIC_API_KEY"] = key
    data = upload.getvalue()
    with tempfile.TemporaryDirectory() as d:
        gloss = Glossary()
        for f in gloss_files or []:
            fp = Path(d) / Path(f.name).name  # basename only: no path components from the client
            fp.write_bytes(f.getvalue())
            gloss.extend(import_file(fp))
        fp = Path(d) / Path(upload.name).name
        fp.write_bytes(data)
        ocr = {"claude": ocr_claude, "tesseract": ocr_tesseract}.get(ocr_kind, lambda: None)()
        with st.spinner("Extraction…"):
            paragraphs = extract_paragraphs(fp, ocr)
        if ctx.before_translate:
            try:
                ctx.before_translate(sum(len(p) for p in paragraphs), upload.name)
            except Exception as e:  # quota or policy refusal, shown to the user and nothing is sent to a model
                st.error(str(e))
                return
        with st.spinner("Traduction…"):
            out = translate_document(build_chat(",".join(provider), None, allow_free), paragraphs, src, tgt, gloss, mode,
                                     juris, tm=TranslationMemory(tm_path))
        out_path = Path(d) / f"{Path(upload.name).stem}_{tgt}.docx"
        build_docx(out, tgt, str(out_path))
        st.session_state["docx"] = (out_path.name, out_path.read_bytes())
        st.session_state["pairs"] = list(zip(paragraphs, out))
        st.session_state["issues"] = [m for s_, t_ in st.session_state["pairs"]
                                      for m in checks.compare(s_, t_).issues()] + [
            f"« {t.source} » doit être « {t.target} »" for s_, t_ in st.session_state["pairs"]
            for t in gloss.missing_in(s_, t_)]
    if ctx.after_translate:
        ctx.after_translate(hashlib.sha256(data).hexdigest(), upload.name)
