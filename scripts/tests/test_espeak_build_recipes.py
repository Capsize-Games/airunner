"""Isolated regression coverage for the locked eSpeak source/build recipes."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[2]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


INTAKE = load_module("espeak_source_intake", "scripts/intake_espeak_source.py")
BUILDER = load_module("espeak_payload_builder", "scripts/build_espeak_native_payload.py")


LICENSES = ("COPYING", "COPYING.APACHE", "COPYING.BSD2", "COPYING.UCD")


def write_archive(path: Path, *, member_name: str | None = None, symlink: str | None = None) -> None:
    with tarfile.open(path, "w:gz") as archive:
        if member_name is not None:
            info = tarfile.TarInfo(member_name)
            content = b"escape"
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
            return
        source = tarfile.TarInfo("espeak-ng/CMakeLists.txt")
        content = b"cmake_minimum_required(VERSION 3.8)\n"
        source.size = len(content)
        archive.addfile(source, io.BytesIO(content))
        for filename in LICENSES:
            license_info = tarfile.TarInfo(f"espeak-ng/{filename}")
            license_content = f"notice:{filename}\n".encode()
            license_info.size = len(license_content)
            archive.addfile(license_info, io.BytesIO(license_content))
        if symlink is not None:
            link = tarfile.TarInfo("espeak-ng/src/include/bad-link")
            link.type = tarfile.SYMTYPE
            link.linkname = symlink
            archive.addfile(link)


def build_lock(archive_path: Path, patch_path: Path) -> dict:
    license_ids = {}
    for name in LICENSES:
        content = f"notice:{name}\n".encode()
        license_ids[name] = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    return {
        "schema_version": 1,
        "upstream": {"commit": "a" * 40, "tree": "b" * 40},
        "source_archive": {
            "filename": archive_path.name,
            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            "size_bytes": archive_path.stat().st_size,
        },
        "patches": [{"filename": patch_path.name, "sha256": hashlib.sha256(patch_path.read_bytes()).hexdigest()}],
        "license_git_blob_ids": license_ids,
        "target": {"cmake_targets": ["espeak-ng-bin", "data"]},
    }


class IntakeTests(unittest.TestCase):
    def test_tree_mismatch_rejects_before_archive_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / "source-lock.json"
            lock_path.write_text(json.dumps({
                "upstream": {"commit": "a" * 40, "tree": "b" * 40},
                "source_archive": {"filename": "locked.tar.gz", "sha256": "c" * 64, "size_bytes": 1},
            }))
            output = root / "output"
            with (
                mock.patch.object(INTAKE, "LOCK", lock_path),
                mock.patch.object(INTAKE, "git", side_effect=["commit", "d" * 40]),
                mock.patch.object(INTAKE.subprocess, "Popen") as popen,
                mock.patch.object(sys, "argv", ["intake", "--git-dir", str(root), "--output-dir", str(output)]),
            ):
                with self.assertRaisesRegex(SystemExit, "unexpected tree"):
                    INTAKE.main()
                popen.assert_not_called()
                self.assertFalse(output.exists())


class BuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.archive = self.root / "synthetic-espeak.tar.gz"
        write_archive(self.archive)
        self.patch = self.root / "patch.diff"
        self.patch.write_text("synthetic patch\n")
        self.lock = self.root / "source-lock.json"
        self.lock.write_text(json.dumps(build_lock(self.archive, self.patch)))
        self.output = self.root / "output"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def call_builder(self) -> int:
        with mock.patch.object(sys, "argv", [
            "builder", "--source-archive", str(self.archive), "--output-dir", str(self.output),
        ]):
            return BUILDER.main()

    def use_test_lock(self) -> None:
        self.enterContext(mock.patch.object(BUILDER, "LOCK_PATH", self.lock))
        self.enterContext(mock.patch.object(BUILDER, "PATCH_PATH", self.patch))
        self.enterContext(mock.patch.object(BUILDER, "require_target_environment"))

    def test_archive_mismatch_rejects_before_extraction_or_commands(self) -> None:
        self.use_test_lock()
        locked = json.loads(self.lock.read_text())
        locked["source_archive"]["sha256"] = "0" * 64
        self.lock.write_text(json.dumps(locked))
        with (
            mock.patch.object(BUILDER, "safe_unpack") as unpack,
            mock.patch.object(BUILDER, "run") as run,
        ):
            with self.assertRaisesRegex(SystemExit, "hash or size"):
                self.call_builder()
            unpack.assert_not_called()
            run.assert_not_called()

    def test_rejects_archive_path_traversal_and_escaping_symlink(self) -> None:
        for bad_name, bad_link in (
            ("espeak-ng/../../escape", None),
            ("other/file", None),
            (None, "../../../escape"),
        ):
            with self.subTest(member=bad_name, link=bad_link):
                malicious = self.root / "malicious.tar.gz"
                write_archive(malicious, member_name=bad_name, symlink=bad_link)
                destination = self.root / "extract"
                destination.mkdir(exist_ok=True)
                with self.assertRaises(ValueError):
                    BUILDER.safe_unpack(malicious, destination)
                self.assertFalse((self.root / "escape").exists())

    def test_allows_relative_symlink_that_stays_in_source_root(self) -> None:
        archive = self.root / "in-tree-link.tar.gz"
        write_archive(archive, symlink="../voices/en")
        destination = self.root / "safe-extract"
        destination.mkdir()
        source = BUILDER.safe_unpack(archive, destination)
        self.assertTrue((source / "src/include/bad-link").is_symlink())

    def test_platform_guard_rejects_non_target_architecture(self) -> None:
        with mock.patch.object(BUILDER.platform, "machine", return_value="aarch64"):
            with self.assertRaisesRegex(SystemExit, "Ubuntu 24.04 x86_64"):
                BUILDER.require_target_environment()

    def test_platform_guard_rejects_non_ubuntu_distribution(self) -> None:
        with (
            mock.patch.object(BUILDER.platform, "machine", return_value="x86_64"),
            mock.patch.object(BUILDER.Path, "read_text", return_value='ID=debian\nVERSION_ID="13"\n'),
        ):
            with self.assertRaisesRegex(SystemExit, "Ubuntu 24.04"):
                BUILDER.require_target_environment()

    def test_command_timeout_has_bounded_failure_evidence(self) -> None:
        process = mock.Mock(pid=12345)
        process.wait.side_effect = [BUILDER.subprocess.TimeoutExpired(["compiler"], 2), -15]

        def fake_popen(command, *, stdout, stderr, **kwargs):
            stdout.write(b"o" * (BUILDER.MAX_EVIDENCE_CHARS + 100))
            stderr.write(b"e" * (BUILDER.MAX_EVIDENCE_CHARS + 100))
            return process

        with (
            mock.patch.object(BUILDER.subprocess, "Popen", side_effect=fake_popen),
            mock.patch.object(BUILDER.os, "killpg") as killpg,
        ):
            with self.assertRaisesRegex(RuntimeError, "timed out after 2s") as raised:
                BUILDER.run(["compiler"], timeout=2)
        self.assertLess(len(str(raised.exception)), BUILDER.MAX_EVIDENCE_CHARS * 3)
        self.assertEqual(killpg.call_args_list[0].args[1], BUILDER.signal.SIGTERM)
        self.assertEqual(killpg.call_args_list[-1].args[1], BUILDER.signal.SIGKILL)

    def test_configure_is_offline_and_payload_receipt_has_source_and_notices(self) -> None:
        self.use_test_lock()
        commands: list[tuple[list[str], dict | None]] = []

        def fake_run(command, *, cwd=None, env=None, timeout=None):
            commands.append((command, env))
            if command[:2] == ["cmake", "--install"]:
                stage = Path(env["DESTDIR"])
                executable = stage / "usr/bin/espeak-ng"
                executable.parent.mkdir(parents=True)
                executable.write_bytes(b"synthetic executable")
                data_file = stage / "usr/share/espeak-ng-data/voices/en/en-us"
                data_file.parent.mkdir(parents=True)
                data_file.write_bytes(b"synthetic data")
            if command == ["cmake", "--version"]:
                return "cmake version 3.31.6"
            if command == ["cc", "--version"]:
                return "cc (Ubuntu 14.2.0)"
            return ""

        with mock.patch.object(BUILDER, "run", side_effect=fake_run):
            self.call_builder()

        configure = next(command for command, _ in commands if command[:2] == ["cmake", "-S"])
        self.assertIn("-DFETCHCONTENT_FULLY_DISCONNECTED=ON", configure)
        for option in (
            "-DUSE_LIBSONIC=OFF", "-DUSE_MBROLA=OFF", "-DUSE_LIBPCAUDIO=OFF",
            "-DUSE_SPEECHPLAYER=OFF", "-DUSE_ASYNC=OFF", "-DUSE_KLATT=ON",
            "-DESPEAK_COMPAT=OFF", "-DESPEAK_BUILD_MANPAGES=OFF",
        ):
            self.assertIn(option, configure)
        build = next(command for command, _ in commands if command[:2] == ["cmake", "--build"])
        self.assertEqual(build[4:6], ["espeak-ng-bin", "data"])
        self.assertTrue(all("--target" in command for command, _ in commands if command[:2] == ["cmake", "--build"]))
        patch_text = (REPO / "packaging/espeak/0001-offline-no-playback.patch").read_text()
        self.assertNotIn("+  FetchContent_MakeAvailable", patch_text)
        self.assertIn("automatic source downloads are disabled", patch_text)

        payload = self.output / "payload"
        for filename in LICENSES:
            staged_notice = payload / "licenses/espeak-ng" / filename
            self.assertTrue(staged_notice.is_file())
            self.assertEqual(staged_notice.read_text(), f"notice:{filename}\n")
        self.assertTrue((payload / "source/synthetic-espeak.tar.gz").is_file())
        self.assertTrue((payload / "source/patch.diff").is_file())
        self.assertTrue((payload / "source/source-lock.json").is_file())
        self.assertTrue((payload / "source/intake_espeak_source.py").is_file())
        self.assertTrue((payload / "source/build_espeak_native_payload.py").is_file())
        self.assertTrue((payload / "source/BUILD.md").is_file())
        receipt = json.loads((payload / "build-receipt.json").read_text())
        self.assertEqual(receipt["source_commit"], "a" * 40)
        self.assertIn("bin/espeak-ng", receipt["files_sha256"])
        self.assertIn("share/espeak-ng-data/voices/en/en-us", receipt["files_sha256"])
        self.assertIn("licenses/espeak-ng/COPYING", receipt["files_sha256"])
        self.assertIn("source/intake_espeak_source.py", receipt["files_sha256"])


if __name__ == "__main__":
    unittest.main()
