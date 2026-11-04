"""Streamlit page of the superagent: profile and memory, translation job, certification, apostille dossier.

Used by saas_app.py (one profile and one work folder per firm) and by app.py. No private key is ever uploaded through
this page: a real signing certificate is configured on the server by its administrator (`aminos superagent set cert ...`);
without one, certification produces a clearly marked SPECIMEN.
"""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

import streamlit as st

from ..glossary import Glossary, import_file
from ..providers import build_chat
from ..tm import TranslationMemory
from . import apostille, stamp
from .agent import JobError, Superagent
from .profile import Profile

ALLOWED_IMPORT = {".md", ".txt"}
MAX_ZIP_FILES, MAX_ZIP_BYTES = 200, 20_000_000


def safe_extract(zf: zipfile.ZipFile, dest: Path) -> int:
    """Extract text files only; reject absolute paths, '..', oversized archives. Returns the number of files written."""
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_ZIP_FILES or sum(i.file_size for i in infos) > MAX_ZIP_BYTES:
        raise ValueError("archive trop volumineuse")
    n = 0
    for i in infos:
        p = PurePosixPath(i.filename)
        if p.is_absolute() or ".." in p.parts or "\\" in i.filename:
            raise ValueError(f"chemin refusé : {i.filename}")
        if p.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}:
            continue
        target = dest / Path(*p.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(i))
        n += 1
    return n


def render_superagent(profile_dir: str | Path, work_dir: str | Path, providers: list[str], default_provider: str,
                      remote_allowed: bool, tm_path: str,
                      before: Callable[[int, str], None] | None = None, after: Callable[[str, str], None] | None = None) -> None:
    prof = Profile(profile_dir)
    st.caption("Mémoire, instructions et paramètres sont propres à votre cabinet. Rien n'est certifié sans relecture humaine.")
    t_job, t_profile = st.tabs(["Dossier de traduction", "Profil et mémoire"])
    with t_profile:
        _profile_tab(prof)
    with t_job:
        _job_tab(prof, work_dir, providers, default_provider, remote_allowed, tm_path, before, after)


def _profile_tab(prof: Profile) -> None:
    params = prof.params
    st.subheader("Traducteur (figure sur le certificat)")
    with st.form("translator"):
        tr = params["translator"]
        c = st.columns(2)
        name = c[0].text_input("Nom", tr["name"])
        cap = c[1].text_input("Qualité (ex. traducteur assermenté près la cour d'appel de …)", tr["capacity"])
        reg = c[0].text_input("N° d'inscription / d'agrément", tr["registration"])
        place = c[1].text_input("Lieu", tr["place"])
        stamp_up = st.file_uploader("Image de VOTRE cachet (PNG fond transparent)", type=["png"])
        sig_up = st.file_uploader("Image de VOTRE signature (PNG fond transparent)", type=["png"])
        if st.form_submit_button("Enregistrer"):
            prof.set_param("translator", {"name": name, "capacity": cap, "registration": reg, "place": place})
            for up, key, fn in ((stamp_up, "stamp_image", "stamp.png"), (sig_up, "signature_image", "signature.png")):
                if up:
                    if not up.getvalue().startswith(b"\x89PNG"):
                        st.error("Fichier PNG attendu.")
                        continue
                    (prof.root / fn).write_bytes(up.getvalue())
                    prof.set_param(key, str(prof.root / fn))
            st.success("Enregistré.")
    real = bool((params["cert"] and params["key"]) or params.get("p12"))
    st.info("Certificat de signature : " + ("configuré sur le serveur (signature réelle)." if real else
            "aucun. La certification produira un ESSAI non officiel. L'administrateur configure le vôtre sur le serveur."))

    st.subheader("Instructions du cabinet")
    new = st.text_area("Règles injectées dans chaque traduction", prof.instructions, height=220)
    if st.button("Enregistrer les instructions"):
        (prof.root / "instructions.md").write_text(new, encoding="utf-8")
        st.success("Enregistré.")

    st.subheader("Mémoire")
    q = st.text_input("Rechercher (laisser vide pour tout voir)")
    for n in (prof.search(q, 20) if q else prof.notes()[-30:]):
        c1, c2 = st.columns([10, 1])
        c1.write(f"{n.text}  \n:grey[{n.origin or 'saisie'}]")
        if c2.button("✕", key=f"forget{n.id}"):
            prof.forget(n.id)
            st.rerun()
    with st.form("note"):
        text = st.text_area("Nouvelle note (préférence, règle d'un client, décision passée)")
        if st.form_submit_button("Ajouter") and text.strip():
            prof.remember(text, origin="saisie")
            st.rerun()

    st.subheader("Importer d'un compte Claude ou d'un autre outil")
    st.caption("Exportez vos instructions (CLAUDE.md), notes de mémoire et dossiers de skills, puis déposez-les ici (.md, .txt ou une archive .zip). "
               "Seuls des textes sont importés ; les scripts ne sont jamais copiés ni exécutés ; les conversations ne sont pas importées.")
    ups = st.file_uploader("Fichiers ou archive", accept_multiple_files=True, type=["md", "txt", "zip"], key="import")
    if ups and st.button("Importer"):
        with tempfile.TemporaryDirectory() as d:
            try:
                for u in ups:
                    if u.name.lower().endswith(".zip"):
                        safe_extract(zipfile.ZipFile(io.BytesIO(u.getvalue())), Path(d))
                    else:
                        (Path(d) / Path(u.name).name).write_bytes(u.getvalue())
                rep = prof.import_claude_export(d)
                st.success(f"{rep['notes']} note(s), {len(rep['skills'])} skill(s), instructions : {rep['instructions'] or 'aucune'}")
                for s in rep["skipped"]:
                    st.caption(f"ignoré : {s}")
            except (ValueError, zipfile.BadZipFile) as e:
                st.error(str(e))
    if prof.skills():
        st.caption("Skills du profil : " + ", ".join(prof.skills()))


def _job_tab(prof, work_dir, providers, default_provider, remote_allowed, tm_path, before, after) -> None:
    c = st.columns(4)
    src = c[0].selectbox("Langue source", ["arabe", "français", "anglais", "néerlandais"])
    tgt = c[1].selectbox("Langue cible", ["français", "arabe", "anglais", "néerlandais"])
    chosen = c[2].multiselect("Modèles (ordre = repli)", providers, default=[default_provider] if default_provider in providers else [])
    free = remote_allowed and c[3].checkbox("J'accepte l'envoi du texte à un tiers")
    juris = st.text_input("Juridiction", prof.params["jurisdiction"])
    gl = st.file_uploader("Glossaires", accept_multiple_files=True, type=["csv", "tsv", "txt", "json", "xlsx", "docx"], key="jgl")
    up = st.file_uploader("Document à traduire", type=["docx", "pdf", "txt"])
    if up and chosen and st.button("Lancer le dossier", type="primary"):
        with tempfile.TemporaryDirectory() as d:
            fp = Path(d) / Path(up.name).name
            fp.write_bytes(up.getvalue())
            g = Glossary()
            for f in gl or []:
                gp = Path(d) / Path(f.name).name
                gp.write_bytes(f.getvalue())
                g.extend(import_file(gp))
            try:
                from ..extract import extract_paragraphs
                if before:
                    before(sum(len(p) for p in extract_paragraphs(fp, None)), up.name)
                sa = Superagent(prof, work_dir, [build_chat(p, None, free) for p in chosen], g, TranslationMemory(tm_path))
                with st.spinner("Traduction, contrôles et reprises en cours…"):
                    job = sa.run(fp, src, tgt, jurisdiction=juris)
                st.session_state["sa_job"] = job.state["id"]
                if after:
                    after(job.state["sha256_in"], up.name)
            except Exception as e:  # quota, provider, extraction: shown, nothing is certified
                st.error(str(e))
    jid = st.session_state.get("sa_job")
    if not jid:
        return
    sa = Superagent(prof, work_dir, [lambda m, s: ""], Glossary())
    try:
        job = sa.job(jid)
    except JobError:
        return
    s = job.state
    (st.success if s["status"] != "non_concluant" else st.error)(f"{s['id']} : {s['status']}")
    for m in s.get("issues", [])[:20]:
        st.warning(m)
    if (job.dir / "translation.docx").exists():
        st.download_button("Télécharger le brouillon .docx", (job.dir / "translation.docx").read_bytes(), "traduction.docx")
        with st.expander("Table de relecture"):
            st.markdown((job.dir / "review.md").read_text(encoding="utf-8"))
    st.subheader("Certification (après relecture)")
    who = st.text_input("Relu et validé par")
    accept = st.text_input("Accepter les points restants (motif, facultatif)") if s["status"] == "non_concluant" else ""
    demo = st.checkbox("Essai : certificat et cachet fictifs", value=True)
    if st.button("Certifier") and who.strip():
        try:
            sa.certify(jid, who, demo=demo, accept_issues=accept)
            st.rerun()
        except JobError as e:
            st.error(str(e))
    if s["status"].startswith("certifie"):
        out = job.dir / "certified"
        v = sa.verify(jid)
        (st.success if v["ok"] else st.error)("Signature et registre vérifiés." if v["ok"] else "Vérification : " + "; ".join(v["problems"]))
        if s.get("specimen"):
            st.warning(stamp.SPECIMEN_FR)
        for fn, label in (("translation.certified.pdf", "PDF signé"), ("translation.docx.p7s", "Signature .p7s du .docx"),
                          ("evidence.json", "Preuve")):
            st.download_button(label, (out / fn).read_bytes(), fn, key=fn)
        st.subheader("Dossier d'apostille")
        cc = st.columns(3)
        origin, dest, kind = cc[0].text_input("Pays d'émission (code, ex. MA)"), cc[1].text_input("Pays de destination (ex. FR)"), cc[2].text_input("Nature du document")
        if st.button("Assembler le dossier"):
            m = sa.dossier(jid, origin, dest, kind)
            st.session_state["sa_dossier"] = m["status"]
        if (job.dir / "dossier" / "CHECKLIST.md").exists():
            st.markdown((job.dir / "dossier" / "CHECKLIST.md").read_text(encoding="utf-8"))
            st.download_button("Télécharger le dossier (.zip)", apostille.zip_dossier(job.dir / "dossier").read_bytes(), "dossier-apostille.zip")
