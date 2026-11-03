"""Keep PyInstaller warning tolerances tied to reviewed optional importers."""

import json
import hashlib
import re
import tomllib
from pathlib import Path

from scripts.verify_warning_source_reviews import verify_warning_source_reviews

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "release-planning/linux-v1/pyinstaller-warning-dispositions-attempt4.json"
SPEC = ROOT / "packaging/linux/services-bundle-spec.toml"


def test_scoped_allowlist_matches_source_review_evidence():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    spec = tomllib.loads(SPEC.read_text(encoding="utf-8"))
    scoped = spec["warn_allowlist"]["importer_scoped"]

    by_module = {item["missing_module"]: item for item in evidence["dispositions"]}
    assert len(by_module) == len(evidence["dispositions"])
    assert all(not module.startswith("psycopg") for module in by_module)

    expected = {
        item["missing_module"]: sorted({imp["module"] for imp in item["importers"]})
        for item in evidence["dispositions"]
        if item["allowlist"]
    }
    actual = {item["module"]: sorted(item["importers"]) for item in scoped}
    assert len(actual) == len(scoped), "scoped warning modules must be unique"
    assert {k: v for k, v in actual.items() if not k.startswith("psycopg")} == expected

    for item in evidence["dispositions"]:
        assert item["importers"], item["missing_module"]
        if item["allowlist"]:
            assert item["rationale"].strip()
            for importer in item["importers"]:
                assert re.fullmatch(r"[0-9a-f]{64}", importer["source_sha256"])
                assert importer["source"] and not importer["source"].startswith("/")
                if importer["imports"]:
                    assert all(site["statement"] and site["source_line"] for site in importer["imports"])
                else:
                    assert item.get("analysis_evidence"), item["missing_module"]
        else:
            assert item["missing_module"] not in actual


def test_required_postgresql_warning_names_remain_unreviewed():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    spec = tomllib.loads(SPEC.read_text(encoding="utf-8"))
    scoped_names = {item["module"] for item in spec["warn_allowlist"]["importer_scoped"]}
    assert scoped_names.intersection({"psycopg", "psycopg.adapt", "psycopg.pq", "psycopg.types"}) == set()
    assert {"psycopg2", "psycopg_c", "psycopg_binary"} <= scoped_names
    assert all(not item["missing_module"].startswith("psycopg") for item in evidence["dispositions"])
    assert "PostgreSQL is retained" in evidence["scope"]


def test_evidence_records_analysis_identity_and_resolved_runtime_edges():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == 1
    assert re.fullmatch(r"[0-9a-f]{40}", evidence["analysis_commit"])
    assert re.fullmatch(r"[0-9a-f]{64}", evidence["source_inputs"]["runtime_lock_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", evidence["source_inputs"]["bundle_spec_sha256"])
    sitecustomize = next(item for item in evidence["dispositions"] if item["missing_module"] == "sitecustomize")
    assert sitecustomize["allowlist"] is True
    assert sitecustomize["importers"][0]["source"] == "stdlib/site.py"
    assert sitecustomize["importers"][0]["source_context"]["lines"] == "644-654"
    bootloader = sitecustomize["bootstrap_evidence"]
    assert bootloader["upstream"] == "PyInstaller bootloader v6.12.0"
    assert "site_import = 0" in bootloader["excerpt"]
    assert bootloader["search_paths"] == "base_library.zip; lib-dynload; application_home_dir"
    assert re.fullmatch(r"[0-9a-f]{64}", bootloader["excerpt_sha256"])

    posix = next(item for item in evidence["dispositions"] if item["missing_module"] == "posixpath.isreserved")
    assert posix["allowlist"] is True
    assert posix["analysis_evidence"]["warn_line"].startswith("missing module named posixpath.isreserved")
    twisted = next(item for item in posix["importers"] if item["module"] == "twisted.python.filepath")
    assert twisted["imports"][0]["line"] == 93
    assert "sys.platform == \"win32\"" in posix["analysis_evidence"]["twisted_source"]


def test_optional_language_helpers_do_not_define_app_language_limits():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    by_name = {item["missing_module"]: item for item in evidence["dispositions"]}
    assert "does not request jieba" in by_name["jieba"]["rationale"]
    assert "makes no claim that the application rejects Chinese" in by_name["jieba"]["rationale"]
    assert "does not constrain input language" not in " ".join(item["rationale"] for item in evidence["dispositions"])
    assert not any("not part of the declared Linux services profile" in item["rationale"] for item in evidence["dispositions"])


def test_source_update_invalidates_review_without_importing_package(tmp_path):
    installed = tmp_path / "site"
    installed.mkdir()
    source = installed / "optional_caller.py"
    source.write_bytes(b"raise RuntimeError('must not execute during review')\n")
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "schema_version": 1,
        "dispositions": [{"importers": [{
            "source": "optional_caller.py",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }]}],
    }))
    assert verify_warning_source_reviews(evidence, site_packages=installed) == []
    source.write_bytes(b"changed package source\n")
    assert verify_warning_source_reviews(evidence, site_packages=installed) == [
        "reviewed warning source changed: optional_caller.py"
    ]
    source.unlink()
    assert verify_warning_source_reviews(evidence, site_packages=installed) == [
        "reviewed warning source unavailable: optional_caller.py"
    ]


def test_source_review_rejects_escape_and_conflicting_hashes(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"outside installation")
    installed = tmp_path / "site"
    installed.mkdir()
    (installed / "redirect.py").symlink_to(outside)
    entry = {"source": "redirect.py", "source_sha256": hashlib.sha256(outside.read_bytes()).hexdigest()}
    evidence = tmp_path / "evidence.json"
    data = {"schema_version": 1, "dispositions": [{"importers": [entry]}]}
    evidence.write_text(json.dumps(data))
    assert verify_warning_source_reviews(evidence, site_packages=installed) == [
        "reviewed warning source unavailable: redirect.py"
    ]
    data["dispositions"][0]["importers"].append({**entry, "source_sha256": "0" * 64})
    evidence.write_text(json.dumps(data))
    assert verify_warning_source_reviews(evidence, site_packages=installed) == [
        "conflicting source hashes in warning evidence"
    ]
