"""Web interface: streamlit run app.py

Run it locally for certified translations: the HMAC key file is read from the machine running the app
and must never be deployed to a shared server.
"""
import os
import tempfile
from pathlib import Path

import streamlit as st

from aminos import certify as cert
from aminos import checks
from aminos.docx_out import build_docx
from aminos.extract import extract_paragraphs, ocr_claude, ocr_tesseract
from aminos.glossary import Glossary, import_file
from aminos.memory import open_memory
from aminos.pipeline import translate_document
from aminos.providers import PROVIDERS, build_chat

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
    tm_backend = st.selectbox("Mémoire de traduction", ["sqlite", "chroma"])
    tm_path = st.text_input("Fichier (sqlite) ou dossier (chroma)", "tm.sqlite" if tm_backend == "sqlite" else "tm_chroma")
    gloss_files = st.file_uploader("Glossaires", accept_multiple_files=True,
                                   type=["csv", "tsv", "txt", "json", "xlsx", "docx", "pdf"])

tab_translate, tab_review, tab_cert = st.tabs(["1. Traduction", "2. Relecture", "3. Certification"])

# ---- 1. translation -----------------------------------------------------------
with tab_translate:
    upload = st.file_uploader("Document à traduire", type=["docx", "pdf", "txt", "png", "jpg", "jpeg", "webp"])
    if upload and st.button("Traduire", type="primary"):
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key
        try:
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
                chat = build_chat(",".join(provider) or "anthropic", None, allow_free)
                with st.spinner("Traduction…"):
                    out = translate_document(chat, paragraphs, src, tgt, gloss, mode, juris,
                                             tm=open_memory(tm_path, tm_backend))
                out_path = Path(d) / f"{Path(upload.name).stem}_{tgt}.docx"
                build_docx(out, tgt, str(out_path))
                st.session_state["docx"] = (out_path.name, out_path.read_bytes())
        except (PermissionError, RuntimeError, ValueError) as e:
            st.error(str(e))
        else:
            st.session_state["pairs"] = list(zip(paragraphs, out))
            st.session_state["gloss"] = gloss
            st.session_state["final"] = "\n\n".join(out)
            st.session_state.pop("cert", None)

    if "docx" in st.session_state:
        name, data = st.session_state["docx"]
        st.download_button("Télécharger le .docx", data, name)
        st.info("Étape suivante : relire et corriger dans l'onglet « Relecture ».")

# ---- 2. review ------------------------------------------------------------------
with tab_review:
    if "pairs" not in st.session_state:
        st.caption("Traduisez d'abord un document.")
    else:
        edited = st.text_area("Traduction (paragraphes séparés par une ligne vide, **gras** conservé)",
                              st.session_state["final"], height=320)
        paras = [p.strip() for p in edited.split("\n\n") if p.strip()]
        st.session_state["final"] = "\n\n".join(paras)
        sources = [s_ for s_, _ in st.session_state["pairs"]]
        issues = checks.compare("\n".join(sources), "\n".join(paras)).issues() + [
            f"« {t.source} » doit être « {t.target} »"
            for t in st.session_state["gloss"].missing_in("\n".join(sources), "\n".join(paras))]
        if len(paras) != len(sources):
            issues.append(f"Segments : source {len(sources)}, traduction {len(paras)}")
        for issue in issues:
            st.warning(issue)
        if not issues:
            st.success("Contrôles terminologie et nombres : RAS")
        with st.expander("Source / traduction côte à côte"):
            for s_, t_ in st.session_state["pairs"]:
                c1, c2 = st.columns(2)
                c1.markdown(s_)
                c2.markdown(t_)

# ---- 3. certification --------------------------------------------------------------
with tab_cert:
    st.warning("À utiliser en local : la clé HMAC reste sur cette machine, ne la déployez jamais sur un serveur "
               "partagé et ne la joignez à aucune livraison.")
    if "pairs" not in st.session_state:
        st.caption("Traduisez et relisez d'abord un document.")
    else:
        c1, c2, c3 = st.columns(3)
        key_file = c1.text_input("Fichier clé HMAC", "cle-hmac.key")
        registry = c2.text_input("Registre", "registre-certifications.csv")
        out_dir = c3.text_input("Dossier de sortie", "archive")
        if not Path(key_file).exists() and st.button("Créer la clé HMAC"):
            cert.make_key(key_file)
            st.success(f"Clé créée : {key_file}")
        if Path(key_file).exists():
            date = st.date_input("Date de l'acte").isoformat()
            if st.button("Générer le document certifié"):
                paras = [p for p in st.session_state["final"].split("\n\n") if p.strip()]
                try:
                    st.session_state["cert"] = cert.certify(paras, src, tgt, key_file, registry, out_dir, date=date)
                except (ValueError, FileExistsError) as e:
                    st.error(str(e))
            info = st.session_state.get("cert")
            if info:
                n = cert.page_count(info["path"])
                st.success(f"Référence {info['ref']} — pages : {n if n else 'non contrôlé (LibreOffice absent)'}")
                if n and n > 1:
                    st.error("Le document dépasse une page : raccourcissez ou réduisez la police avant de certifier.")
                st.download_button("Télécharger le .docx certifié (non scellé)", Path(info["path"]).read_bytes(),
                                   Path(info["path"]).name)
                st.subheader("Évaluation")
                st.caption("Seuil : fidélité 5/5, autres ≥ 4/5. Aucune certification sans validation d'Alami.")
                scores = {k: st.number_input(cert.CRITERIA_LABEL[k], 0, 5, 5 if k == "fidelite" else 4, key=f"s_{k}")
                          for k in cert.CRITERIA}
                points = st.text_area("Points à confirmer sur l'original (un par ligne)", "")
                ev = cert.Evaluation(scores, [p for p in points.splitlines() if p.strip()])
                if not ev.passes():
                    st.error("Seuil non atteint : reprendre la traduction avant de soumettre.")
                validated = st.checkbox("Validation d'Alami : les points ci-dessus ont été contrôlés sur l'original")
                if st.button("Sceller", disabled=not (ev.passes() and validated)):
                    eval_dir = Path(registry).resolve().parent / "evaluations"  # never inside the archive folder
                    eval_dir.mkdir(exist_ok=True)
                    eval_path = eval_dir / f"{info['ref']}.md"
                    cert.write_evaluation(eval_path, info["ref"], ev)
                    eval_path.write_text(eval_path.read_text(encoding="utf-8")
                                         .replace("Validation Alami : non", "Validation Alami : oui"), encoding="utf-8")
                    try:
                        seal = cert.seal(info["path"], key_file, registry, info["ref"], eval_path)
                    except (PermissionError, ValueError) as e:
                        st.error(str(e))
                    else:
                        st.success(f"{info['ref']} scellé ({seal[:12]}…)")
                        st.download_button("Télécharger le .docx scellé", Path(info["path"]).read_bytes(),
                                           Path(info["path"]).name, key="dl_sealed")
