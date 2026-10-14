"""Throw-away test PKI. The CA name says what it is; never use it for real documents."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

CA_NAME = "AMINOS TEST CA - NON QUALIFIE - ESSAI UNIQUEMENT"


def _name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Aminos test bench"),
                      x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _write_key(path: Path, key) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))


def _pem(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def create_test_pki(out_dir: str | Path, signer_cn: str = "Test Signataire Fictif", days: int = 30) -> dict[str, Path]:
    """Write ca.pem (public), signer.pem, signer.key and chain.pem under out_dir; return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)
    ca_key, key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())

    ca = (x509.CertificateBuilder().subject_name(_name(CA_NAME)).issuer_name(_name(CA_NAME))
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now).not_valid_after(now + dt.timedelta(days=days))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA256()))
    cert = (x509.CertificateBuilder().subject_name(_name(signer_cn)).issuer_name(ca.subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now).not_valid_after(now + dt.timedelta(days=days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256()))

    paths = {"ca": out / "ca.pem", "cert": out / "signer.pem", "key": out / "signer.key", "chain": out / "chain.pem"}
    paths["ca"].write_bytes(_pem(ca))
    paths["cert"].write_bytes(_pem(cert))
    paths["chain"].write_bytes(_pem(cert) + _pem(ca))
    _write_key(paths["key"], key)
    # the CA private key is discarded on purpose: no further certificates can ever be issued
    return paths
