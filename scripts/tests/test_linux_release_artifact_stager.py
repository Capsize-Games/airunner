"""Offline contract checks for exact-hash wheel staging."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.request
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage_linux_release_artifacts as stager


class RedirectResponse:
    headers = {}


class FakeWheelResponse:
    headers = {"Content-Length": "4"}

    def __init__(self) -> None:
        self._chunks = [b"abc"]

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def geturl(self) -> str:
        return "https://files.pythonhosted.org/packages/demo.whl"

    def read(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class FakeOpener:
    def open(self, _request, timeout: int):
        return FakeWheelResponse()


class DurableResponse:
    def __init__(self, url: str, payload: bytes) -> None:
        self._url = url
        self._payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self, size: int) -> bytes:
        payload, self._payload = self._payload[:size], self._payload[size:]
        return payload


class DurableOpener:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error

    def open(self, request, timeout: int):
        assert timeout == 120
        if self.error is not None:
            raise self.error
        assert request.full_url == self.response.geturl()
        return self.response


class LinuxReleaseArtifactStagerTests(unittest.TestCase):
    def _durable_fixture(self, root: Path, payload: bytes = b"verified wheel"):
        filename = "demo_package-1.0-py3-none-any.whl"
        digest = hashlib.sha256(payload).hexdigest()
        url = f"https://github.com/Capsize-Games/airunner/releases/download/v6.1.9/{filename}"
        lock = (
            "demo-package==1.0 \\\n"
            f"    --hash=sha256:{digest}\n"
        )
        lock_path = root / "requirements.txt"
        lock_path.write_text(lock, encoding="utf-8")
        row = {
            "name": "demo-package",
            "version": "1.0",
            "filename": filename,
            "sha256": digest,
            "size_bytes": len(payload),
            "source": {
                "kind": "actions_artifact",
                "repo": "Capsize-Games/airunner",
                "artifact_id": 123,
                "run_id": 456,
                "artifact_name": "test-wheel-artifact",
                "source_revision": "a" * 40,
                "archive_sha256": "b" * 64,
                "max_archive_bytes": 4096,
                "durable_release_url": url,
            },
        }
        manifest = {
            "schema_version": 1,
            "status": "candidate-only; not activated",
            "durable_release_tag": "v6.1.9",
            "selected_count": 1,
            "selected_lock_sha256": hashlib.sha256(lock.encode()).hexdigest(),
            "artifact_sources": [row],
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return filename, payload, url, lock_path, manifest_path

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

    def test_failed_https_hash_check_removes_partial_output(self) -> None:
        content_hash = hashlib.sha256(b"abcd").hexdigest()
        spec = {"filename": "demo.whl", "size_bytes": 4, "sha256": content_hash}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "demo.whl"
            with mock.patch.object(stager.urllib.request, "build_opener", return_value=FakeOpener()):
                with self.assertRaisesRegex(stager.StageError, "download size or digest mismatch"):
                    stager.download_https("https://files.pythonhosted.org/demo.whl", target, spec)
            self.assertFalse(target.exists())

    def test_published_durable_wheel_needs_no_actions_token_or_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            filename, payload, url, lock_path, manifest_path = self._durable_fixture(root)
            output = root / "staged"
            with mock.patch.dict(os.environ, {}, clear=True), \
                    mock.patch.object(stager.urllib.request, "build_opener", return_value=DurableOpener(
                        DurableResponse(url, payload)
                    )), \
                    mock.patch.object(stager, "_verify_action_groups", side_effect=AssertionError("Actions metadata requested")), \
                    mock.patch.object(stager, "actions_zip", side_effect=AssertionError("Actions archive requested")):
                receipt = stager.stage(manifest_path, lock_path, output)
            self.assertEqual((output / filename).read_bytes(), payload)
            self.assertEqual(receipt["wheels"][0]["source_kind"], "durable_release")
            route = receipt["source_routes"][0]
            self.assertEqual(route["selected_route"], "durable_release")
            self.assertEqual(route["durable_release_url"], url)
            self.assertEqual(route["original_actions_source"]["artifact_id"], 123)

    def test_durable_404_falls_back_to_the_exact_actions_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            filename, payload, url, lock_path, manifest_path = self._durable_fixture(root)
            output = root / "staged"
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr(filename, payload)
            archive.seek(0)
            missing = urllib.error.HTTPError(url, 404, "not published", None, None)
            with mock.patch.dict(os.environ, {"GH_TOKEN": "fixture-token"}, clear=True), \
                    mock.patch.object(stager.urllib.request, "build_opener", return_value=DurableOpener(error=missing)), \
                    mock.patch.object(stager, "_verify_action_groups", return_value={("Capsize-Games/airunner", 123): 8192}) as metadata, \
                    mock.patch.object(stager, "actions_zip", return_value=archive) as actions:
                receipt = stager.stage(manifest_path, lock_path, output)
            self.assertEqual((output / filename).read_bytes(), payload)
            self.assertEqual(receipt["wheels"][0]["source_kind"], "actions_artifact")
            self.assertEqual(receipt["source_routes"][0]["selected_route"], "actions_artifact")
            metadata.assert_called_once()
            actions.assert_called_once()

    def test_non_404_durable_error_does_not_fall_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _filename, _payload, url, lock_path, manifest_path = self._durable_fixture(root)
            output = root / "staged"
            denied = urllib.error.HTTPError(url, 503, "upstream unavailable", None, None)
            with mock.patch.dict(os.environ, {"GH_TOKEN": "fixture-token"}, clear=True), \
                    mock.patch.object(stager.urllib.request, "build_opener", return_value=DurableOpener(error=denied)), \
                    mock.patch.object(stager, "_verify_action_groups", side_effect=AssertionError("must not fall back")):
                with self.assertRaisesRegex(stager.StageError, "HTTP 503"):
                    stager.stage(manifest_path, lock_path, output)

    def test_durable_hash_mismatch_does_not_fall_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _filename, payload, url, lock_path, manifest_path = self._durable_fixture(root, b"verified")
            output = root / "staged"
            wrong = b"verifieD"
            with mock.patch.dict(os.environ, {"GH_TOKEN": "fixture-token"}, clear=True), \
                    mock.patch.object(stager.urllib.request, "build_opener", return_value=DurableOpener(
                        DurableResponse(url, wrong)
                    )), \
                    mock.patch.object(stager, "_verify_action_groups", side_effect=AssertionError("must not fall back")):
                with self.assertRaisesRegex(stager.StageError, "digest mismatch"):
                    stager.stage(manifest_path, lock_path, output)
            self.assertFalse((output / "demo_package-1.0-py3-none-any.whl").exists())

    def test_all_durable_routes_are_validated_before_any_download(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _filename, _payload, _url, lock_path, manifest_path = self._durable_fixture(root)
            manifest = json.loads(manifest_path.read_text())
            manifest["artifact_sources"][0]["source"]["durable_release_url"] = (
                "https://github.com/Capsize-Games/airunner/releases/download/v6.1.8/demo_package-1.0-py3-none-any.whl"
            )
            manifest_path.write_text(json.dumps(manifest))
            output = root / "staged"
            with mock.patch.object(stager.urllib.request, "build_opener", side_effect=AssertionError("network before validation")):
                with self.assertRaisesRegex(stager.StageError, "noncanonical durable"):
                    stager.stage(manifest_path, lock_path, output)
            self.assertFalse(output.exists())

    def test_failed_actions_wheel_hash_check_removes_partial_output(self) -> None:
        content = b"abc"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "artifact.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("demo-1.0-py3-none-any.whl", content)
            out = root / "out"
            out.mkdir()
            with archive_path.open("rb") as archive:
                with self.assertRaisesRegex(stager.StageError, "digest mismatch"):
                    stager.extract_actions_wheels(
                        archive, [{"filename": "demo-1.0-py3-none-any.whl",
                                   "sha256": hashlib.sha256(b"different").hexdigest(),
                                   "size_bytes": len(content)}], out,
                    )
            self.assertFalse((out / "demo-1.0-py3-none-any.whl").exists())

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
        ownership_handoff = workflow.split("sudo chown", 1)[1].split("\n          sudo unshare", 1)[0]
        self.assertIn("triton-3.7.1+capsize.2-", ownership_handoff)
        verify_output = workflow.index("subset differs from reviewed pin")
        ownership_change = workflow.index("sudo chown")
        receipt_binding = workflow.index("- name: Bind the safe output to this workflow run")
        self.assertLess(verify_output, ownership_change)
        self.assertLess(ownership_change, receipt_binding)
        self.assertIn("sudo unshare --net", workflow[workflow.rfind("sudo unshare --net", 0, verify_output):verify_output])


if __name__ == "__main__":
    unittest.main()
