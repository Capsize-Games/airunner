"""Archive and tool boundaries for the offline libzim candidate probe."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import libzim_candidate_probe as probe
import runtime_wheel_hardening as hardening


class LibzimCandidateProbeTests(unittest.TestCase):
    def _wheel(self, members: dict[str, bytes]) -> zipfile.ZipFile:
        record = "libzim-3.7.0.dist-info/RECORD"
        members[record] = hardening.rewrite_record(members | {record: b""}, record)
        temp = tempfile.NamedTemporaryFile(suffix=".whl", delete=False)
        temp.close()
        with zipfile.ZipFile(temp.name, "w") as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
        self.addCleanup(Path(temp.name).unlink, missing_ok=True)
        return zipfile.ZipFile(temp.name)

    def test_valid_wheel_archive_verifies_full_record_and_unique_payloads(self):
        native = b"synthetic native payload"
        with self._wheel({
            "libzim/libzim.so.9": native,
            "libzim/extension.so": b"synthetic Python extension",
            "libzim-3.7.0.dist-info/METADATA": b"Name: libzim\nVersion: 3.7.0\n\n",
        }) as archive:
            rows, member, digest, metadata, extension_member, extension_hash = (
                probe._verify_wheel_archive(archive)
            )

        self.assertEqual(rows, 3)
        self.assertEqual(member, "libzim/libzim.so.9")
        self.assertEqual(digest, hashlib.sha256(native).hexdigest())
        self.assertEqual(metadata, "libzim-3.7.0.dist-info/METADATA")
        self.assertEqual(extension_member, "libzim/extension.so")
        self.assertEqual(extension_hash, hashlib.sha256(b"synthetic Python extension").hexdigest())

    def test_zip_rejects_traversal_and_noncanonical_paths(self):
        for name in ("../escape", "pkg\\..\\escape", "/absolute"):
            with self.subTest(name=name), self._wheel_archive_with_single_member(name) as archive:
                with self.assertRaises(ValueError):
                    probe._verify_wheel_archive(archive)

    def _wheel_archive_with_single_member(self, name: str) -> zipfile.ZipFile:
        temp = tempfile.NamedTemporaryFile(suffix=".whl", delete=False)
        temp.close()
        with zipfile.ZipFile(temp.name, "w") as archive:
            archive.writestr(name, b"bad")
        self.addCleanup(Path(temp.name).unlink, missing_ok=True)
        return zipfile.ZipFile(temp.name)

    def test_zip_rejects_duplicate_and_symlink_members(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate_path = Path(directory) / "duplicate.whl"
            with zipfile.ZipFile(duplicate_path, "w") as archive:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr("pkg/data", b"one")
                    archive.writestr("pkg/data", b"two")
            with zipfile.ZipFile(duplicate_path) as archive:
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    probe._verify_wheel_archive(archive)

            symlink_path = Path(directory) / "symlink.whl"
            info = zipfile.ZipInfo("pkg/link")
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            with zipfile.ZipFile(symlink_path, "w") as archive:
                archive.writestr(info, b"target")
            with zipfile.ZipFile(symlink_path) as archive:
                with self.assertRaisesRegex(ValueError, "symbolic-link"):
                    probe._verify_wheel_archive(archive)

    def test_record_rejects_unlisted_payload(self):
        with self._wheel({
            "libzim/libzim.so.9": b"native",
            "libzim-3.7.0.dist-info/METADATA": b"Name: libzim\nVersion: 3.7.0\n\n",
        }) as archive:
            members = {info.filename: archive.read(info) for info in archive.infolist()}
        members["unlisted"] = b"extra"
        path = "libzim-3.7.0.dist-info/RECORD"
        with self.assertRaisesRegex(ValueError, "membership mismatch"):
            hardening.verify_record(members, path)

    def test_readelf_calls_have_finite_timeout(self):
        completed = type("Result", (), {"stdout": " 0x00000001 (NEEDED) Shared library: [libc.so.6]"})()
        with patch.object(probe.subprocess, "run", return_value=completed) as run:
            probe._dynamic_info(Path("candidate.so"))

        self.assertEqual(run.call_count, 3)
        self.assertTrue(all(call.kwargs["timeout"] == 60 for call in run.call_args_list))

    def test_source_paths_are_repository_relative_and_canonical(self):
        for value in ("../etc/passwd", "/etc/passwd", "C:\\private"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe._repo_file(value)


if __name__ == "__main__":
    unittest.main()
