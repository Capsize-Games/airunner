"""Offline stdlib tests for the llama.cpp wheel notice transformation."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import complete_llama_cpp_wheel_notices as completion
    import dependency_notices
finally:
    sys.path.remove(str(ROOT / "scripts"))

WHEEL_NAME = completion.WHEEL_NAME
DIST = completion.DIST_INFO
PROVENANCE = ROOT / "packaging/licenses/llama-cpp-python-0.3.21-capsize.3-wheel-provenance"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_row(name: str, data: bytes) -> list[str]:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")
    return [name, f"sha256={encoded}", str(len(data))]


def _write_input_wheel(path: Path) -> dict[str, bytes]:
    metadata_name = f"{DIST}/METADATA"
    record_name = f"{DIST}/RECORD"
    wrapper_license_name = f"{DIST}/licenses/LICENSE.md"
    initial = {
        metadata_name: (
            b"Metadata-Version: 2.1\nName: llama_cpp_python\n"
            b"Version: 0.3.21+capsize.3\nLicense: MIT\n\n"
        ),
        wrapper_license_name: (PROVENANCE / "LICENSE-wrapper.md").read_bytes(),
        f"{DIST}/WHEEL": b"Wheel-Version: 1.0\n",
        "llama_cpp/__init__.py": (PROVENANCE / "llama_cpp__init__.py").read_bytes(),
        "llama_cpp/_llama_cpp.so": b"native binary fixture\x00\x01",
    }
    rows = [_record_row(name, content) for name, content in sorted(initial.items())]
    rows.append([record_name, "", ""])
    record = io.StringIO(newline="")
    csv.writer(record, lineterminator="\n").writerows(rows)
    initial[record_name] = record.getvalue().encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as wheel:
        for name, content in sorted(initial.items()):
            wheel.writestr(name, content)
    return initial


class NoticeCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)
        self.repo = self.tmp / "repo"
        provenance = self.repo / "packaging/licenses/llama-cpp-python-0.3.21-capsize.3-wheel-provenance"
        provenance.mkdir(parents=True)
        for path in PROVENANCE.iterdir():
            if path.is_file():
                (provenance / path.name).write_bytes(path.read_bytes())
        self.input_wheel = self.tmp / WHEEL_NAME
        self.initial = _write_input_wheel(self.input_wheel)
        build_manifest = "\n".join(
            f"{key}={value}" for key, value in completion.BUILD_FIELDS.items()
        ).encode("utf-8") + b"\n"
        self.artifact = self.tmp / "build-artifact.zip"
        with zipfile.ZipFile(self.artifact, "w", zipfile.ZIP_DEFLATED) as outer:
            outer.writestr("BUILD-MANIFEST.txt", build_manifest)
            outer.write(self.input_wheel, WHEEL_NAME)
        self.manifest_path = provenance / "transform-input.json"
        self.manifest = json.loads((PROVENANCE / "transform-input.json").read_text())
        self.manifest["input_wheel"].update(
            sha256=_sha(self.input_wheel.read_bytes()), size_bytes=self.input_wheel.stat().st_size
        )
        self.manifest["producer_artifact"].update(
            archive_sha256=_sha(self.artifact.read_bytes()), archive_size_bytes=self.artifact.stat().st_size
        )
        self.manifest["build_manifest"].update(sha256=_sha(build_manifest), size_bytes=len(build_manifest))
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")
        overrides = {
            "EXPECTED_WHEEL_SHA256": self.manifest["input_wheel"]["sha256"],
            "EXPECTED_WHEEL_SIZE": self.manifest["input_wheel"]["size_bytes"],
            "EXPECTED_ARTIFACT_SHA256": self.manifest["producer_artifact"]["archive_sha256"],
            "EXPECTED_ARTIFACT_SIZE": self.manifest["producer_artifact"]["archive_size_bytes"],
            "EXPECTED_BUILD_MANIFEST_SHA256": self.manifest["build_manifest"]["sha256"],
            "EXPECTED_BUILD_MANIFEST_SIZE": self.manifest["build_manifest"]["size_bytes"],
        }
        for name, value in overrides.items():
            item = patch.object(completion, name, value)
            item.start()
            self.addCleanup(item.stop)

    def _complete(self, folder: str = "out"):
        directory = self.tmp / folder
        directory.mkdir(exist_ok=True)
        output = directory / WHEEL_NAME
        receipt = directory / "receipt.json"
        result = completion.complete_wheel(
            self.input_wheel, self.artifact, self.manifest_path, output, receipt
        )
        return output, receipt, result

    def test_payload_notices_record_and_output_are_deterministic(self):
        out_a, _receipt_a, first = self._complete("out-a")
        out_b, _receipt_b, second = self._complete("out-b")
        self.assertEqual(out_a.read_bytes(), out_b.read_bytes())
        self.assertEqual(first["output_wheel"]["sha256"], second["output_wheel"]["sha256"])
        with zipfile.ZipFile(out_a) as after:
            for name, content in self.initial.items():
                if not name.endswith(("/METADATA", "/RECORD")):
                    self.assertEqual(after.read(name), content)
            metadata = after.read(f"{DIST}/METADATA").decode()
            self.assertIn("Metadata-Version: 2.4\n", metadata)
            self.assertEqual(
                [line.removeprefix("License-File: ") for line in metadata.splitlines() if line.startswith("License-File: ")],
                ["LICENSE.md", "llama.cpp/LICENSE", "llama.cpp/licenses/LICENSE-jsonhpp"],
            )
            rows = list(csv.reader(io.StringIO(after.read(f"{DIST}/RECORD").decode())))
            mapping = {row[0]: row for row in rows}
            self.assertEqual(set(mapping), set(after.namelist()))
            for name in after.namelist():
                self.assertEqual(mapping[name], [name, "", ""] if name.endswith("/RECORD") else _record_row(name, after.read(name)))
            self.assertEqual(first["original_zip_member_count"], len(self.initial))
            self.assertEqual(first["output_zip_member_count"], len(self.initial) + 2)
            self.assertEqual(len(rows), len(self.initial) + 2)
            self.assertEqual(first["output_record_row_count"], len(rows))
            self.assertEqual(first["preserved_original_member_count"], len(self.initial) - 2)

    def test_production_collector_reads_all_three_declared_notices(self):
        output, _receipt, _result = self._complete("completed")
        prefix = self.tmp / "python"
        site = prefix / "lib/python3.13/site-packages"
        site.mkdir(parents=True)
        prefix_patch = patch.object(dependency_notices.sys, "prefix", str(prefix))
        prefix_patch.start()
        self.addCleanup(prefix_patch.stop)
        with zipfile.ZipFile(output) as wheel:
            for name in wheel.namelist():
                if name.startswith(f"{DIST}/"):
                    target = site / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(wheel.read(name))
        lock = self.repo / "constraints.txt"
        lock.write_text(
            f"llama-cpp-python==0.3.21+capsize.3 \\\n    --hash=sha256:{_sha(output.read_bytes())}\n"
        )
        spec = {
            "bundle": {"constraints": lock.name},
            "profile": {"services_extra": "test-fixture"},
            "dependency_notices": {"required": True, "dest": "legal/dependencies", "manifest": "dependency-notices.json"},
        }
        bundle = self.tmp / "bundle"
        bundle.mkdir()
        dependency_notices.collect_dependency_notices(spec, self.repo, bundle, site_packages=[site])
        package = json.loads((bundle / "legal/dependencies/dependency-notices.json").read_text())["distributions"][0]
        self.assertEqual((package["name"], package["version"], len(package["notices"])), ("llama_cpp_python", "0.3.21+capsize.3", 3))

    def test_tampered_input_and_unsafe_evidence_path_are_rejected(self):
        output = self.tmp / "blocked" / WHEEL_NAME
        receipt = self.tmp / "blocked" / "receipt.json"
        tampered = self.tmp / "tampered.whl"
        tampered.write_bytes(self.input_wheel.read_bytes() + b"tamper")
        with self.assertRaisesRegex(completion.NoticeWheelError, "input wheel hash"):
            completion.complete_wheel(tampered, self.artifact, self.manifest_path, output, receipt)
        self.manifest["wrapper_source"]["evidence_path"] = "../outside"
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(completion.NoticeWheelError, "wrapper Git member identity"):
            completion.complete_wheel(self.input_wheel, self.artifact, self.manifest_path, output, receipt)
        self.assertFalse(output.exists())

    def test_changed_notice_bytes_are_rejected(self):
        notice = self.repo / "packaging/licenses/llama-cpp-python-0.3.21-capsize.3-wheel-provenance/LICENSE-llama.cpp.txt"
        notice.write_bytes(b"altered notice")
        output = self.tmp / "blocked" / WHEEL_NAME
        with self.assertRaisesRegex(completion.NoticeWheelError, "notice bytes"):
            completion.complete_wheel(self.input_wheel, self.artifact, self.manifest_path, output, output.with_suffix(".json"))
        self.assertFalse(output.exists())

    def test_tampered_build_artifact_is_rejected_before_output(self):
        tampered = self.tmp / "tampered-artifact.zip"
        tampered.write_bytes(self.artifact.read_bytes() + b"tamper")
        output = self.tmp / "blocked" / WHEEL_NAME
        with self.assertRaisesRegex(completion.NoticeWheelError, "CI artifact ZIP hash or size"):
            completion.complete_wheel(self.input_wheel, tampered, self.manifest_path, output, output.with_suffix(".json"))
        self.assertFalse(output.exists())

    def test_output_cannot_replace_input(self):
        with self.assertRaisesRegex(completion.NoticeWheelError, "separate from all inputs"):
            completion.complete_wheel(self.input_wheel, self.artifact, self.manifest_path, self.input_wheel, self.tmp / "receipt.json")
        self.assertTrue(self.input_wheel.is_file())


if __name__ == "__main__":
    unittest.main()
