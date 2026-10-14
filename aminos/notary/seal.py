"""Seals: detached CMS (PKCS#7, any file such as .docx) and embedded PAdES-style signature (PDF).

Detached CMS is created with `cryptography` and verified with `openssl cms`, so an independent
implementation confirms every seal. PDF signing and validation use pyHanko.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7


def seal_detached(file: str | Path, key: str | Path, cert: str | Path, ca: str | Path,
                  out: str | Path | None = None) -> Path:
    """Write <file>.p7s (DER, detached, SHA-256) and return its path."""
    data = Path(file).read_bytes()
    priv = serialization.load_pem_private_key(Path(key).read_bytes(), None)
    builder = (pkcs7.PKCS7SignatureBuilder().set_data(data)
               .add_signer(x509.load_pem_x509_certificate(Path(cert).read_bytes()), priv, hashes.SHA256())
               .add_certificate(x509.load_pem_x509_certificate(Path(ca).read_bytes())))
    sig = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary])
    out = Path(out) if out else Path(str(file) + ".p7s")
    out.write_bytes(sig)
    return out


def verify_detached(file: str | Path, sig: str | Path, ca: str | Path) -> tuple[bool, str]:
    """Verify with OpenSSL against `ca` only. Returns (ok, openssl message)."""
    with tempfile.NamedTemporaryFile() as sink:
        p = subprocess.run(["openssl", "cms", "-verify", "-binary", "-inform", "DER", "-in", str(sig),
                            "-content", str(file), "-CAfile", str(ca), "-purpose", "any", "-no_check_time",
                            "-out", sink.name], capture_output=True, text=True)
    return p.returncode == 0, (p.stderr or p.stdout).strip()


def seal_pdf(pdf_in: str | Path, pdf_out: str | Path, key: str | Path, cert: str | Path, ca: str | Path,
             reason: str = "Integrity seal (test)") -> Path:
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    signer = signers.SimpleSigner.load(str(key), str(cert), ca_chain_files=(str(ca),))
    meta = signers.PdfSignatureMetadata(field_name="Signature1", md_algorithm="sha256", reason=reason)
    with open(pdf_in, "rb") as src, open(pdf_out, "wb") as dst:
        signers.sign_pdf(IncrementalPdfFileWriter(src), meta, signer=signer, output=dst)
    return Path(pdf_out)


def verify_pdf(pdf: str | Path, ca: str | Path) -> dict:
    """{'signatures': n, 'intact': bool, 'valid': bool, 'trusted': bool, 'signer': str}."""
    from pyhanko.keys import load_cert_from_pemder
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext
    ctx = ValidationContext(trust_roots=[load_cert_from_pemder(str(ca))])
    with open(pdf, "rb") as f:
        sigs = PdfFileReader(f).embedded_signatures
        if not sigs:
            return {"signatures": 0, "intact": False, "valid": False, "trusted": False, "signer": ""}
        st = validate_pdf_signature(sigs[-1], ctx)
        return {"signatures": len(sigs), "intact": bool(st.intact), "valid": bool(st.valid),
                "trusted": bool(st.trusted), "signer": sigs[-1].signer_cert.subject.human_friendly}
