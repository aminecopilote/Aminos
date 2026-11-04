"""Visual layer of a certified translation: stamp image, translator's statement page, page footers.

Everything here is drawing. It carries no legal weight by itself: the legal weight comes from the translator's own stamp
image, signature and certificate, which the translator supplies. Without them the output is a SPECIMEN, labelled as such
on every page, so it cannot be mistaken for an official document.
"""
from __future__ import annotations

import io
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

LANG_NAMES = {
    "fr": {"ar": "arabe", "fr": "français", "en": "anglais", "nl": "néerlandais"},
    "en": {"ar": "Arabic", "fr": "French", "en": "English", "nl": "Dutch"},
    "nl": {"ar": "Arabisch", "fr": "Frans", "en": "Engels", "nl": "Nederlands"},
    "ar": {"ar": "العربية", "fr": "الفرنسية", "en": "الإنجليزية", "nl": "الهولندية"},
}
_ALIASES = {"arabe": "ar", "arabic": "ar", "français": "fr", "francais": "fr", "french": "fr", "anglais": "en",
            "english": "en", "néerlandais": "nl", "neerlandais": "nl", "dutch": "nl", "nederlands": "nl"}

SPECIMEN_FR = ("DOCUMENT D'ESSAI : cachet et signature NON OFFICIELS. Ne constitue ni une traduction assermentée, "
               "ni une légalisation, ni une apostille.")

TEXTS = {
    "fr": {
        "title": "CERTIFICATION DE TRADUCTION",
        "body": ("Je soussigné(e) {name}{capacity}, certifie que la traduction ci-jointe, de la langue {src} vers la langue "
                 "{tgt}, du document intitulé « {doc} », est complète et fidèle à l'original qui m'a été présenté."),
        "reviewed": "Traduction relue et validée par : {who}",
        "made": "Fait à {place}, le {date}.",
        "h_src": "Empreinte SHA-256 de l'original", "h_tr": "Empreinte SHA-256 de la traduction",
        "footer": "Traduction conforme à l'original · page {i}/{n}",
        "signer": "Signature du traducteur",
    },
    "en": {
        "title": "CERTIFICATE OF TRANSLATION",
        "body": ("I, the undersigned {name}{capacity}, certify that the attached translation from {src} into {tgt} of the "
                 "document entitled \"{doc}\" is complete and faithful to the original presented to me."),
        "reviewed": "Translation reviewed and approved by: {who}",
        "made": "Done at {place}, on {date}.",
        "h_src": "SHA-256 of the original", "h_tr": "SHA-256 of the translation",
        "footer": "Translation true to the original · page {i}/{n}",
        "signer": "Translator's signature",
    },
    "nl": {
        "title": "VERKLARING VAN VERTALING",
        "body": ("Ik, ondergetekende {name}{capacity}, verklaar dat de bijgevoegde vertaling uit het {src} in het {tgt} van "
                 "het document \"{doc}\" volledig en getrouw is aan het mij voorgelegde origineel."),
        "reviewed": "Vertaling nagelezen en goedgekeurd door: {who}",
        "made": "Opgemaakt te {place}, op {date}.",
        "h_src": "SHA-256 van het origineel", "h_tr": "SHA-256 van de vertaling",
        "footer": "Vertaling conform het origineel · pagina {i}/{n}",
        "signer": "Handtekening van de vertaler",
    },
    "ar": {
        "title": "شهادة ترجمة",
        "body": ("أنا الموقع أدناه {name}{capacity}، أشهد بأن الترجمة المرفقة من اللغة {src} إلى اللغة {tgt} "
                 "للوثيقة المعنونة «{doc}» كاملة ومطابقة للأصل الذي عُرض علي."),
        "reviewed": "روجعت الترجمة وأُقرت من طرف: {who}",
        "made": "حرر بـ {place}، في {date}.",
        "h_src": "بصمة SHA-256 للأصل", "h_tr": "بصمة SHA-256 للترجمة",
        "footer": "ترجمة مطابقة للأصل · صفحة {i}/{n}",
        "signer": "توقيع المترجم",
    },
}

_FONTS = {
    "latin": [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"],
    "arabic": [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\tahoma.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf", "/Library/Fonts/Arial.ttf"],
}


def lang_code(lang: str) -> str:
    low = lang.strip().lower()
    return low if low in LANG_NAMES["fr"] else _ALIASES.get(low, low[:2])


def find_font(arabic: bool = False) -> str | None:
    env = os.environ.get("AMINOS_FONT")
    if env and Path(env).is_file():
        return env
    return next((p for p in _FONTS["arabic" if arabic else "latin"] if Path(p).is_file()), None)


def _register(arabic: bool) -> str:
    """Register a TTF (needed for Arabic and for characters beyond Latin-1); fall back to Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    path = find_font(arabic)
    if not path:
        return "Helvetica"
    name = "AminosArabic" if arabic else "AminosSans"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, path))
    return name


def shape(text: str, lang: str) -> str:
    """Arabic needs letter joining and right-to-left reordering before a PDF canvas can draw it."""
    if lang_code(lang) != "ar":
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError as e:
        raise RuntimeError("Arabic output needs: pip install arabic-reshaper python-bidi") from e
    return get_display(arabic_reshaper.reshape(text))


def make_stamp_png(path: str | Path, lines: list[str], specimen: bool = True, size: int = 480,
                   color: tuple[int, int, int] = (28, 58, 140)) -> Path:
    """A round stamp with centred lines. With specimen=True a diagonal ESSAI band makes it unusable as an official stamp."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    for r, w in ((c - 6, 8), (c - 26, 3)):
        d.ellipse((c - r, c - r, c + r, c + r), outline=color + (255,), width=w)
    fp = find_font(False)
    try:
        font = ImageFont.truetype(fp, size // 17) if fp else ImageFont.load_default()
        big = ImageFont.truetype(fp, size // 11) if fp else ImageFont.load_default()
    except OSError:
        font = big = ImageFont.load_default()
    lines = [l for l in lines if l.strip()][:5]
    gap = size // 14
    y = c - gap * (len(lines) - 1) // 2
    for i, line in enumerate(lines):
        f = big if i == 0 else font
        w = d.textlength(line, font=f)
        d.text((c - w / 2, y - gap // 3), line, fill=color + (255,), font=f)
        y += gap
    if specimen:
        band = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        bd = ImageDraw.Draw(band)
        bd.rectangle((0, c - size // 12, size, c + size // 12), fill=(200, 30, 30, 170))
        label = "ESSAI · NON OFFICIEL"
        w = bd.textlength(label, font=big)
        bd.text((c - w / 2, c - size // 22), label, fill=(255, 255, 255, 255), font=big)
        img = Image.alpha_composite(img, band.rotate(25, resample=Image.BICUBIC))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return Path(path)


def qr_png(payload: str) -> bytes | None:
    try:
        import qrcode
    except ImportError:
        return None
    buf = io.BytesIO()
    qrcode.make(payload, box_size=4, border=1).save(buf, format="PNG")
    return buf.getvalue()


def build_certificate_pdf(out: str | Path, *, doc_name: str, src_lang: str, tgt_lang: str, sha_src: str, sha_tr: str,
                          translator: dict, reviewed_by: str, date: str, cert_lang: str | None = None,
                          stamp_png: str | Path | None = None, signature_png: str | Path | None = None,
                          specimen: bool = True, qr_payload: str = "") -> tuple[Path, tuple[float, float, float, float]]:
    """One A4 page. Returns (path, signature box in PDF points) so a digital signature can sit on the signature area.

    The statement is written in `cert_lang` (default: the language of the target document, or French).
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader, simpleSplit
    from reportlab.pdfgen import canvas

    code = cert_lang or (lang_code(tgt_lang) if lang_code(tgt_lang) in TEXTS else "fr")
    if code == "ar" and not find_font(True):
        code = "fr"  # no Arabic-capable font on this machine: do not print broken glyphs
    t = TEXTS[code]
    names = LANG_NAMES[code]
    ar = code == "ar"
    if ar:
        date = date.replace("-", "/")  # python-bidi reverses a hyphenated date inside right-to-left text
    font = _register(ar)
    page_w, page_h = A4
    margin = 56
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle(t["title"])

    def put(text: str, x: float, y: float, size: float = 10.5, bold: bool = False, right: bool = False) -> None:
        c.setFont(font, size)
        s = shape(text, code)
        if right or ar:
            c.drawRightString(page_w - margin if ar else x, y, s)
        else:
            c.drawString(x, y, s)

    def para(text: str, y: float, size: float = 10.5, leading: float = 15) -> float:
        """Wrap the logical text first, then shape and draw each line (right-aligned for Arabic)."""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        words, line, lines = text.split(), "", []
        for w in words:
            cand = f"{line} {w}".strip()
            if line and stringWidth(shape(cand, code), font, size) > page_w - 2 * margin:
                lines.append(line)
                line = w
            else:
                line = cand
        lines.append(line)
        for ln in lines:
            put(ln, margin, y, size)
            y -= leading
        return y

    y = page_h - margin
    if specimen:
        c.setFillColorRGB(0.78, 0.12, 0.12)
        c.setFont(_register(False), 8.5)
        for line in simpleSplit(SPECIMEN_FR, _register(False), 8.5, page_w - 2 * margin):
            c.drawString(margin, y, line)
            y -= 11
        c.setFillColorRGB(0, 0, 0)
        y -= 6
    c.setFont(font, 17)
    title = shape(t["title"], code)
    c.drawCentredString(page_w / 2, y - 14, title)
    y -= 50

    cap = ", ".join(x for x in (translator.get("capacity", ""), translator.get("registration", "")) if x)
    body = t["body"].format(name=translator.get("name") or "…………", capacity=f" ({cap})" if cap else "",
                            src=names.get(lang_code(src_lang), src_lang), tgt=names.get(lang_code(tgt_lang), tgt_lang),
                            doc=doc_name)
    y = para(body, y)
    y -= 10
    if reviewed_by:
        y = para(t["reviewed"].format(who=reviewed_by), y)
    y -= 6
    y = para(t["made"].format(place=translator.get("place") or "…………", date=date), y)
    y -= 14

    for label, h in ((t["h_src"], sha_src), (t["h_tr"], sha_tr)):
        c.setFont(font, 8)
        put(label, margin, y, 8)
        y -= 11
        c.setFont("Courier", 7.5)
        c.drawString(margin, y, h)
        y -= 16

    sig_h, sig_w = 90, 230
    box = (margin, y - sig_h - 20, margin + sig_w, y - 20)
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.rect(*box[:2], sig_w, sig_h)
    c.setFont(font, 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    cap_text = shape(t["signer"], code)
    c.drawString(box[0] + 4, box[1] - 11, cap_text) if not ar else c.drawRightString(box[2], box[1] - 11, cap_text)
    c.setFillColorRGB(0, 0, 0)
    if signature_png and Path(signature_png).is_file():
        c.drawImage(ImageReader(str(signature_png)), box[0] + 8, box[1] + 8, sig_w - 16, sig_h - 16,
                    preserveAspectRatio=True, mask="auto")
    if stamp_png and Path(stamp_png).is_file():
        c.drawImage(ImageReader(str(stamp_png)), page_w - margin - 150, box[1] - 10, 150, 150,
                    preserveAspectRatio=True, mask="auto")
    qr = qr_png(qr_payload) if qr_payload else None
    if qr:
        c.drawImage(ImageReader(io.BytesIO(qr)), margin, margin, 70, 70)
        c.setFont("Helvetica", 6.5)
        c.drawString(margin + 78, margin + 8, "QR : empreinte de la traduction (vérification par comparaison SHA-256)")
    c.showPage()
    c.save()
    return Path(out), box


def stamp_pages(pdf_in: str | Path, pdf_out: str | Path, *, text_lang: str, stamp_png: str | Path | None,
                specimen: bool, sha_tr: str, font_lang: str | None = None) -> Path:
    """Footer on every page (conformity line + short hash) and a small stamp at the bottom right."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    code = text_lang if text_lang in TEXTS else "fr"
    if code == "ar" and not find_font(True):
        code = "fr"
    t, font = TEXTS[code], _register(code == "ar")
    reader = PdfReader(str(pdf_in))
    writer = PdfWriter()
    n = len(reader.pages)
    for i, page in enumerate(reader.pages, 1):
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        c.setFont(font, 7.5)
        c.setFillColorRGB(0.25, 0.25, 0.25)
        line = shape(t["footer"].format(i=i, n=n), code) + f" · SHA-256 {sha_tr[:16]}…"
        if code == "ar":
            c.drawRightString(w - 36, 18, line)
        else:
            c.drawString(36, 18, line)
        if specimen:
            c.setFillColorRGB(0.78, 0.12, 0.12)
            c.setFont(_register(False), 7)
            c.drawString(36, 8, "ESSAI : cachet et signature non officiels")
        if stamp_png and Path(stamp_png).is_file():
            c.drawImage(ImageReader(str(stamp_png)), w - 36 - 70, 8, 70, 70, preserveAspectRatio=True, mask="auto")
        c.save()
        buf.seek(0)
        writer.add_page(page)
        writer.pages[-1].merge_page(PdfReader(buf).pages[0])
    with open(pdf_out, "wb") as f:
        writer.write(f)
    return Path(pdf_out)


def append_pdf(first: str | Path, second: str | Path, out: str | Path) -> Path:
    from pypdf import PdfWriter
    wr = PdfWriter()
    for p in (first, second):
        wr.append(str(p))
    with open(out, "wb") as f:
        wr.write(f)
    return Path(out)


def docx_to_pdf(docx: str | Path, outdir: str | Path) -> Path | None:
    """LibreOffice headless. Returns None when LibreOffice is not installed (the caller then ships the .docx only)."""
    exe = (shutil.which("soffice") or shutil.which("libreoffice")
           or next((p for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe") if Path(p).is_file()), None))
    if not exe:
        return None
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:  # private profile: no clash with a running instance
        p = subprocess.run([exe, f"-env:UserInstallation={Path(profile).as_uri()}", "--headless", "--convert-to", "pdf",
                            "--outdir", str(outdir), str(docx)], capture_output=True, text=True, timeout=180)
    pdf = outdir / (Path(docx).stem + ".pdf")
    return pdf if p.returncode == 0 and pdf.exists() else None


def today() -> str:
    import datetime
    return datetime.date.today().isoformat()
