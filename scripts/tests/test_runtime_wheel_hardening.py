"""Focused, standard-library coverage for deterministic wheel rewriting."""

from __future__ import annotations

import csv
import hashlib
import io
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_wheel_hardening as hardening


class RuntimeWheelHardeningTests(unittest.TestCase):
    def test_distribution_selection_is_explicit_and_rejects_unknown_names(self) -> None:
        data = {"artifacts": [{"distribution": "allowed"}, {"distribution": "held"}]}
        self.assertEqual(hardening.select_artifacts(data, ["allowed"]), [{"distribution": "allowed"}])
        for selection in (["unknown"], ["allowed", "allowed"]):
            with self.assertRaises(ValueError):
                hardening.select_artifacts(data, selection)

    def test_archive_paths_reject_traversal(self) -> None:
        for path in ("../outside", "/absolute", "pkg/../../outside", "a/./b", "a//b", "C:\\outside", "", "a\x00b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                hardening.checked_relative(path)

    def test_output_filename_cannot_escape_directory(self) -> None:
        for filename in ("nested/a.whl", "../a.whl", "/a.whl", "a.txt"):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                hardening.checked_filename(filename)

    def test_source_wheel_is_rejected_before_rewriting_invalid_records(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sample-1.0-py3-none-any.whl"
            members = {"sample/data": b"original", "sample-1.0.dist-info/RECORD": b""}
            members["sample-1.0.dist-info/RECORD"] = hardening.rewrite_record(
                members, "sample-1.0.dist-info/RECORD"
            )
            members["sample/data"] = b"tampered"
            with zipfile.ZipFile(source, "w") as archive:
                for path, data in members.items():
                    archive.writestr(path, data)
            spec = {"source_filename": source.name,
                    "source_sha256": hardening.hash_file(source),
                    "candidate_filename": "sample-2.0-py3-none-any.whl"}
            with self.assertRaisesRegex(ValueError, "invalid RECORD"):
                hardening.transform_one(spec, root, root / "out", "unused", "unused", root)
            self.assertFalse((root / "out").exists())

    def test_source_wheel_rejects_duplicate_and_symlink_members(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sample-1.0-py3-none-any.whl"
            for case in ("duplicate", "symlink"):
                with self.subTest(case=case):
                    with zipfile.ZipFile(source, "w") as archive:
                        info = zipfile.ZipInfo("sample/data")
                        info.create_system = 3
                        if case == "symlink":
                            info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(info, b"payload")
                        if case == "duplicate":
                            with self.assertWarns(UserWarning):
                                archive.writestr("sample/data", b"second")
                    spec = {"source_filename": source.name,
                            "source_sha256": hardening.hash_file(source),
                            "candidate_filename": "sample-2.0-py3-none-any.whl"}
                    with self.assertRaisesRegex(ValueError, "duplicate|symbolic link"):
                        hardening.transform_one(spec, root, root / "out", "unused", "unused", root)

    def test_record_hashes_and_membership_are_verified(self) -> None:
        members = {"pkg/data.txt": b"data", "pkg-1.dist-info/RECORD": b""}
        record_path = "pkg-1.dist-info/RECORD"
        members[record_path] = hardening.rewrite_record(members, record_path)
        hardening.verify_record(members, record_path)
        members["pkg/data.txt"] = b"changed"
        with self.assertRaisesRegex(ValueError, "invalid RECORD"):
            hardening.verify_record(members, record_path)

    def test_zip_metadata_uses_fixed_timestamp_and_stable_modes(self) -> None:
        info = hardening.zip_info("a.txt")
        self.assertEqual(info.date_time, hardening.EPOCH)
        self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
        self.assertEqual(info.external_attr >> 16, 0o100644)

    def test_transform_is_repeatable_and_updates_record_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_dir = root / "inputs"
            input_dir.mkdir()
            source = input_dir / "sample-1.0-py3-none-any.whl"
            dist = "sample-1.0.dist-info"
            metadata_path = dist + "/METADATA"
            record_path = dist + "/RECORD"
            source_members = {
                "sample/data.txt": b"payload",
                "sample/optional.bin": b"excluded",
                metadata_path: b"Metadata-Version: 2.1\nName: sample\nVersion: 1.0\n",
                dist + "/WHEEL": b"Wheel-Version: 1.0\n",
                record_path: b"",
            }
            source_members[record_path] = hardening.rewrite_record(source_members, record_path)
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in source_members.items():
                    archive.writestr(name, data)
            source_hash = hardening.hash_file(source)
            extra = root / "extra-license.txt"
            extra.write_text("license\n", encoding="utf-8")
            fake_tool = root / "patchelf"
            fake_tool.write_bytes(b"reviewed-tool-placeholder")
            spec = {
                "source_filename": source.name,
                "source_sha256": source_hash,
                "candidate_filename": "sample-1.0+capsize.1-py3-none-any.whl",
                "old_dist_version_token": "1.0",
                "new_dist_version_token": "1.0+capsize.1",
                "new_version": "1.0+capsize.1",
                "exclude_members": ["sample/optional.bin"],
                "excluded_member_hashes": [{"path": "sample/optional.bin", "sha256": hashlib.sha256(b"excluded").hexdigest()}],
                "elf_patches": [],
                "license_extras": [{"source_path": "extra-license.txt", "wheel_path": "sample-1.0+capsize.1.dist-info/licenses/LICENSE.txt", "sha256": hashlib.sha256(b"license\n").hexdigest()}],
            }
            out_a, out_b = root / "out-a", root / "out-b"
            first = hardening.transform_one(spec, input_dir, out_a, str(fake_tool), "readelf", root)
            second = hardening.transform_one(spec, input_dir, out_b, str(fake_tool), "readelf", root)
            self.assertEqual(first["sha256"], second["sha256"])
            output = out_a / spec["candidate_filename"]
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn("sample/optional.bin", archive.namelist())
                self.assertIn("sample-1.0+capsize.1.dist-info/licenses/LICENSE.txt", archive.namelist())
                metadata = archive.read("sample-1.0+capsize.1.dist-info/METADATA").decode()
                self.assertIn("Version: 1.0+capsize.1\n", metadata)
                rows = list(csv.reader(io.StringIO(archive.read("sample-1.0+capsize.1.dist-info/RECORD").decode())))
                self.assertEqual(len(rows), len(archive.namelist()))


if __name__ == "__main__":
    unittest.main()
