"""Check release security floors against locked and installed package bytes."""

from __future__ import annotations

import hashlib
import io
import re
import ssl
from pathlib import Path

import certifi
from packaging.requirements import Requirement
from packaging.version import Version
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "package" / "constraints-linux-nvidia-cu129.txt"
SERVICES_SETUP = ROOT / "services" / "setup.py"

SECURITY_FLOORS = {
    "certifi": Version("2026.10.23"),
    "pillow": Version("13.0.0"),
}

# Mozilla's removed CA report and the two eMudhra removal bugs identify these
# DER SHA-256 fingerprints. The report is updated over time; the identities
# remain the regression guard rather than a required whole-bundle hash.
# https://ccadb.my.salesforce-sites.com/mozilla/RemovedCACertificateReport
# https://bugzilla.mozilla.org/show_bug.cgi?id=2083449
# https://bugzilla.mozilla.org/show_bug.cgi?id=2083709
MOZILLA_DISTRUSTED_EMSIGN_ROOTS = {
    "125609AA301DA0A249B97A8239CB6A34216F44DCAC9F3954B14292F2E8C8608F",  # C1
    "BC4D809B15189D78DB3E1D8CF4F9726A795DA1643CA5F1358E1DDB0EDC0D7EB3",  # C3
    "86A1ECBA089C4A8D3BBE2734C612BA341D813E043CF9E8A862CD5C57A36BBE6B",  # G3
}


def _locked_block(package: str) -> str:
    lines = LOCK.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(f"{package}==")]
    assert len(starts) == 1, f"expected one {package} lock entry"
    start = starts[0]
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if re.match(r"^[A-Za-z0-9_.-]+==", lines[i])
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _locked_version(package: str) -> Version:
    match = re.match(rf"{re.escape(package)}==([^\s\\]+)", _locked_block(package))
    assert match is not None, f"missing exact lock version for {package}"
    return Version(match.group(1))


def _runtime_requirement(package: str) -> Requirement:
    source = SERVICES_SETUP.read_text(encoding="utf-8")
    matches = re.findall(
        rf'^\s*"{re.escape(package)}([^"\n]+)"\s*,?$', source, re.MULTILINE
    )
    assert len(matches) == 1, f"expected one direct {package} runtime requirement"
    return Requirement(f"{package}{matches[0]}")


def test_linux_lock_meets_security_floors_and_runtime_requirements() -> None:
    for package, floor in SECURITY_FLOORS.items():
        block = _locked_block(package)
        locked = _locked_version(package)
        hashes = re.findall(
            r"(?m)^\s+--hash=sha256:([0-9a-f]{64})\s*$", block
        )
        requirement = _runtime_requirement(package)

        assert locked >= floor
        assert locked in requirement.specifier, (
            f"locked {package} {locked} is outside runtime requirement "
            f"{requirement.specifier}"
        )
        assert hashes, f"{package} lock entry must contain SHA-256 hashes"


def test_certifi_bundle_excludes_mozilla_removed_em_sign_roots() -> None:
    pem_bundle = Path(certifi.where()).read_text(encoding="ascii")
    certificates = re.findall(
        r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
        pem_bundle,
        re.DOTALL,
    )
    observed = {
        hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()
        for pem in certificates
    }
    assert certificates, "certifi bundle contains no PEM certificates"
    assert observed.isdisjoint(MOZILLA_DISTRUSTED_EMSIGN_ROOTS)


def test_pillow_rgba_composite_resize_png_round_trip() -> None:
    background = Image.new("RGBA", (2, 2), (0, 0, 255, 255))
    overlay = Image.new("RGBA", (2, 2), (255, 0, 0, 128))

    composited = Image.alpha_composite(background, overlay)
    resized = composited.resize((4, 4), Image.Resampling.LANCZOS)
    encoded = io.BytesIO()
    resized.save(encoded, format="PNG")
    encoded.seek(0)

    with Image.open(encoded) as opened:
        result = opened.convert("RGBA")

    assert result.size == (4, 4)
    assert result.mode == "RGBA"
    assert result.getpixel((2, 2)) == (128, 0, 127, 255)
