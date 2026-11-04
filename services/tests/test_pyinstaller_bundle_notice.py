"""Keep the shipped PyInstaller bootloader notice tied to its reviewed input."""

import hashlib
import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pyinstaller_bootloader_notice_is_bound_to_exact_builder_wheel():
    manifest = json.loads(
        (ROOT / "package/linux-builder-tools-artifact-sources.json").read_text()
    )
    row = next(item for item in manifest["artifact_sources"] if item["name"] == "pyinstaller")
    provenance = json.loads(
        (ROOT / "packaging/licenses/pyinstaller-6.12.0-provenance.json").read_text()
    )
    notice_path = ROOT / "packaging/licenses/pyinstaller-6.12.0-COPYING.txt"
    notice = notice_path.read_bytes()

    assert row["version"] == provenance["distribution"]["version"] == "6.12.0"
    assert row["filename"] == provenance["selected_wheel"]["filename"]
    assert row["sha256"] == provenance["selected_wheel"]["sha256"]
    assert row["size_bytes"] == provenance["selected_wheel"]["size_bytes"]
    assert row["source"]["url"] == provenance["selected_wheel"]["url"]
    assert hashlib.sha256(notice).hexdigest() == provenance["license_file"]["sha256"]
    assert len(notice) == provenance["license_file"]["size_bytes"]
    assert b"GNU GENERAL PUBLIC LICENSE" in notice
    assert b"Bootloader Exception" in notice
    assert provenance["upstream_source"]["commit"] == "31dbe9ff477716e4790aa317bc9da68766d20659"


def test_full_bundle_stages_raw_bootloader_license_and_provenance():
    spec = tomllib.loads(
        (ROOT / "packaging/linux/services-bundle-spec.toml").read_text()
    )
    root_data = {
        row["source"]: row
        for row in spec["data"]
        if row.get("stage") == "root"
    }
    for source in (
        "packaging/licenses/pyinstaller-6.12.0-COPYING.txt",
        "packaging/licenses/pyinstaller-6.12.0-provenance.json",
    ):
        assert source in root_data
        assert root_data[source]["required"] is True
        assert root_data[source]["dest"] == "legal/third-party"

    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
    assert "PyInstaller 6.12.0 bootloader" in notices
    assert "GPL version 2 or later with the PyInstaller Bootloader Exception" in notices
    assert "31dbe9ff477716e4790aa317bc9da68766d20659" in notices
    assert "a2abf5fde31a8b38b6df7939bcef8ac1d0c51e97e25317ce3555cd675259750f" in notices
