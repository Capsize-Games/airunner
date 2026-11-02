"""Offline contract checks for exact-hash wheel staging."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage_linux_release_artifacts as stager


class RedirectResponse:
    headers = {}


class LinuxReleaseArtifactStagerTests(unittest.TestCase):
    def test_selected_lock_binds_each_pin_and_wheel_hash(self) -> None:
        wheel_hash = hashlib.sha256(b"wheel").hexdigest()
        lock = f"demo-package==1.2.3 \\\n    --hash=sha256:{wheel_hash}\n"
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "requirements.txt"
            lock_path.write_text(lock)
            manifest = {
                "selected_count": 1,
                "selected_lock_sha256": hashlib.sha256(lock.encode()).hexdigest(),
                "artifact_sources": [{"name": "demo-package", "version": "1.2.3", "sha256": wheel_hash}],
            }
            stager.validate_lock(manifest, lock_path)
            manifest["artifact_sources"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(stager.StageError, "pins or hashes"):
                stager.validate_lock(manifest, lock_path)

    def test_lock_digest_mismatch_and_direct_reference_fail(self) -> None:
        wheel_hash = hashlib.sha256(b"wheel").hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "requirements.txt"
            lock_path.write_text("demo-package @ https://example.invalid/demo.whl\n")
            manifest = {
                "selected_count": 1,
                "selected_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                "artifact_sources": [{"name": "demo-package", "version": "1.2.3", "sha256": wheel_hash}],
            }
            with self.assertRaisesRegex(stager.StageError, "direct URLs"):
                stager.validate_lock(manifest, lock_path)
            manifest["selected_lock_sha256"] = "0" * 64
            with self.assertRaisesRegex(stager.StageError, "lock digest"):
                stager.validate_lock(manifest, lock_path)

    def test_repository_path_rejects_traversal(self) -> None:
        for value in ("/package/wheelhouse/a.whl", "package/../outside.whl", "package//wheelhouse/a.whl"):
            with self.subTest(value=value), self.assertRaises(stager.StageError):
                stager.checked_repo_wheel_path(value)

    def test_actions_wheel_extraction_requires_exact_filename_size_and_digest(self) -> None:
        content = b"verified wheel payload"
        digest = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "artifact.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("nested/demo-1.0-py3-none-any.whl", content)
                archive.writestr("receipt.json", "{}")
            with archive_path.open("rb") as archive:
                out = root / "out"
                out.mkdir()
                result = stager.extract_actions_wheels(
                    archive, [{"filename": "demo-1.0-py3-none-any.whl", "sha256": digest,
                               "size_bytes": len(content)}], out,
                )
            self.assertEqual(result[0]["sha256"], digest)
            self.assertEqual((root / "out/demo-1.0-py3-none-any.whl").read_bytes(), content)

    def test_actions_archive_rejects_unsafe_member(self) -> None:
        content = b"payload"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "artifact.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../demo-1.0-py3-none-any.whl", content)
            with archive_path.open("rb") as archive, self.assertRaisesRegex(stager.StageError, "unsafe or duplicate"):
                out = root / "out"
                out.mkdir()
                stager.extract_actions_wheels(
                    archive, [{"filename": "demo-1.0-py3-none-any.whl",
                               "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}], out,
                )

    def test_actions_archive_digest_is_exact(self) -> None:
        archive_bytes = b"zip payload"
        actual = hashlib.sha256(archive_bytes).hexdigest()
        stager.verify_actions_archive_digest(actual, actual)
        with self.assertRaisesRegex(stager.StageError, "archive digest"):
            stager.verify_actions_archive_digest(actual, "0" * 64)

    def test_pending_artifact_fails_before_creating_output(self) -> None:
        wheel_hash = hashlib.sha256(b"wheel").hexdigest()
        lock = f"demo-package==1.2.3 \\\n    --hash=sha256:{wheel_hash}\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock_path = root / "requirements.txt"
            lock_path.write_text(lock)
            manifest_path = root / "manifest.json"
            manifest = {
                "schema_version": 1,
                "status": "candidate-only; not activated",
                "selected_count": 1,
                "selected_lock_sha256": hashlib.sha256(lock.encode()).hexdigest(),
                "artifact_sources": [{
                    "name": "demo-package", "version": "1.2.3", "filename": "demo.whl",
                    "sha256": wheel_hash, "size_bytes": 5, "wheel_tags": ["py3-none-any"],
                    "source": {"kind": "actions_artifact_pending", "filename": "demo.whl"},
                }],
            }
            manifest_path.write_text(json.dumps(manifest))
            output = root / "staged"
            with self.assertRaisesRegex(stager.StageError, "not bound yet"):
                stager.stage(manifest_path, lock_path, output)
            self.assertFalse(output.exists())

    def test_redirect_is_blocked_before_request_and_auth_is_not_forwarded(self) -> None:
        handler = stager.RestrictedRedirect(stager.GITHUB_ACTIONS_HOSTS, allow_actions_storage=True)
        original = urllib.request.Request(
            "https://api.github.com/repos/o/r/actions/artifacts/123/zip",
            headers={"Authorization": "Bearer secret-token", "User-Agent": "test-agent"},
        )
        with self.assertRaisesRegex(stager.StageError, "allowlist"):
            handler.redirect_request(original, RedirectResponse(), 302, "Found", {}, "https://evil.example/file")
        azure = (
            "https://productionresultssa31.blob.core.windows.net/actions-results/"
            "febfd070-806e-8cfb-9381-224a6dd881f0/workflow-job-run-"
            "8c79548a-8cfb-4aa7-a321-0123456789ab/artifacts/" + "a" * 64 + ".zip?sig=temporary&se=x&sv=x&sr=b&sp=r"
        )
        redirected = handler.redirect_request(original, RedirectResponse(), 302, "Found", {}, azure)
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertEqual(redirected.get_header("User-agent"), "test-agent")


class TritonWorkflowContractTests(unittest.TestCase):
    def test_transform_steps_are_network_isolated_and_upload_is_subset_only(self) -> None:
        workflow = Path(".github/workflows/triton-subset-candidate.yml").read_text()
        self.assertGreaterEqual(workflow.count("sudo unshare --net"), 2)
        self.assertIn("sudo unshare --net -- env -i PATH=/usr/bin:/bin LC_ALL=C \\\n            python3 -I -S scripts/runtime_wheel_hardening.py", workflow)
        self.assertIn("sudo unshare --net -- env -i PATH=/usr/bin:/bin LC_ALL=C \\\n            python3 -I -S scripts/build_triton_external_toolchain_subset.py", workflow)
        self.assertIn("class RejectRedirect", workflow)
        candidate = json.loads(Path("package/triton-subset-candidate-input.json").read_text())
        self.assertEqual(candidate["source"]["size_bytes"], 197169871)
        upload = workflow.split("- name: Upload only the reviewed redistributable subset", 1)[1]
        self.assertIn("triton-3.7.1+capsize.2-", upload)
        self.assertNotIn("triton-3.7.1+capsize.1-", upload)
        self.assertNotIn("triton-3.7.1-cp313-", upload)
        self.assertIn("package/triton-external-toolchain-subset.json", upload)
        self.assertIn("candidate_input_sha256", workflow)


if __name__ == "__main__":
    unittest.main()
