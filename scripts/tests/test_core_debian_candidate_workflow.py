"""Static contract checks for the isolated CORE Debian candidate workflow."""

from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/core-debian-candidate.yml"
SMOKE = ROOT / "scripts/core_debian_candidate_smoke.sh"
UPGRADE_SMOKE = ROOT / "scripts/core_debian_upgrade_smoke.sh"
FIXTURE = ROOT / "scripts/create_core_upgrade_fixture.py"


class CoreDebianCandidateWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow_text = WORKFLOW.read_text(encoding="utf-8")
        # BaseLoader preserves GitHub's `on` key as a string.
        cls.workflow = yaml.load(cls.workflow_text, Loader=yaml.BaseLoader)
        cls.smoke = SMOKE.read_text(encoding="utf-8")
        cls.upgrade_smoke = UPGRADE_SMOKE.read_text(encoding="utf-8")
        cls.fixture = FIXTURE.read_text(encoding="utf-8")

    def test_has_only_candidate_triggers_and_read_only_permissions(self):
        self.assertEqual(set(self.workflow["on"]), {"workflow_dispatch", "pull_request"})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertIn("github.event_name == 'pull_request' || github.ref_type == 'branch'", self.workflow_text)
        for path in (
            "scripts/core_debian_candidate_smoke.sh",
            "scripts/core_debian_upgrade_smoke.sh",
            "scripts/create_core_upgrade_fixture.py",
            "scripts/tests/test_core_debian_candidate_workflow.py",
        ):
            self.assertIn(f'"{path}"', self.workflow_text)

    def test_checks_out_exact_candidate_without_persisting_credentials(self):
        self.assertEqual(self.workflow_text.count("persist-credentials: false"), 3)
        self.assertEqual(self.workflow_text.count("ref: ${{ github.event.pull_request.head.sha || github.sha }}"), 3)
        self.assertIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", self.workflow_text)

    def test_every_action_uses_a_full_commit_pin(self):
        for line in self.workflow_text.splitlines():
            if "uses:" in line:
                reference = line.split("uses:", 1)[1].strip()
                self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}(?:\s+# v[0-9]+)?$")

    def test_reviews_inputs_before_binary_only_locked_install(self):
        self.assertIn("--mode verify-record", self.workflow_text)
        self.assertIn("--mode activate", self.workflow_text)
        self.assertIn("apt-get install -y build-essential debhelper-compat dpkg-dev python3-venv", self.workflow_text)
        self.assertIn("pip install --require-hashes --only-binary=:all:", self.workflow_text)
        self.assertIn("-r package/constraints-linux-core.txt", self.workflow_text)
        self.assertIn("pip install --no-deps --no-build-isolation ./services", self.workflow_text)
        self.assertIn("dpkg-buildpackage --build=binary --no-sign", self.workflow_text)
        jobs = self.workflow["jobs"]
        self.assertEqual(jobs["build-core-debian-candidate"]["runs-on"], "ubuntu-24.04")
        self.assertEqual(jobs["clean-install-smoke"]["runs-on"], "ubuntu-26.04")
        self.assertEqual(jobs["published-upgrade-data-smoke"]["runs-on"], "ubuntu-26.04")
        self.assertEqual(jobs["published-upgrade-data-smoke"]["needs"], "build-core-debian-candidate")
        self.assertEqual(jobs["published-upgrade-data-smoke"]["permissions"], {"contents": "read"})
        python_setup = next(
            step
            for step in jobs["build-core-debian-candidate"]["steps"]
            if str(step.get("uses", "")).startswith("actions/setup-python@")
        )
        self.assertEqual(python_setup["with"]["python-version"], "3.13.5")

    def test_artifact_is_bound_to_source_and_lock_and_not_published(self):
        self.assertIn('"source_sha": os.environ["CORE_SOURCE_SHA"]', self.workflow_text)
        self.assertIn('"lock_sha256": digest("package/constraints-linux-core.txt")', self.workflow_text)
        self.assertIn("assert record[\"source_sha\"] == os.environ[\"CORE_SOURCE_SHA\"]", self.workflow_text)
        self.assertIn("assert record[\"debian_sha256\"] == digest(deb)", self.workflow_text)
        self.assertIn("sha256sum --check SHA256SUMS", self.workflow_text)
        self.assertIn('sudo env CORE_SOURCE_SHA="$CORE_SOURCE_SHA"', self.workflow_text)
        self.assertIn('${CORE_SOURCE_SHA:?', self.smoke)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", self.workflow_text)
        self.assertNotIn("secrets.", self.workflow_text)
        for forbidden in ("contents: write", "create-release", "gh release", "aptly", "gpg --"):
            self.assertNotIn(forbidden, self.workflow_text)

    def test_smoke_uses_production_ports_and_authenticated_health_api(self):
        for expected in (
            "systemctl start airunner-headless.service",
            "systemctl stop airunner-headless.service",
            "systemctl restart airunner-headless.service",
            "http://127.0.0.1:8080/health",
            "http://127.0.0.1:8080/api/v1/health/daemon",
            "Authorization: Bearer $api_key",
            "expected 401",
            "assert_stopped",
            "HF_HUB_OFFLINE=1",
            "AIRUNNER_RUNTIME_BIND_HOST=127.0.0.1",
        ):
            self.assertIn(expected, self.smoke)
        self.assertIn('"real model inference and model downloads"', self.smoke)
        self.assertIn('"offline network-denial behavior"', self.smoke)
        self.assertIn('"upgrade preservation from a prior package (covered by separate upgrade validation)"', self.smoke)
        self.assertIn('"APT repository promotion or signing"', self.smoke)
        self.assertIn('"full-ML candidate build"', self.smoke)

    def test_upgrade_smoke_uses_published_prior_package_and_preserves_data(self):
        self.assertIn("Upgrade from published prior package and check synthetic data preservation", self.workflow_text)
        self.assertIn("create_core_upgrade_fixture.py", self.workflow_text)
        self.assertIn("--source-sha \"$CORE_SOURCE_SHA\"", self.workflow_text)
        self.assertIn('assert candidate["lock_sha256"] == digest("package/constraints-linux-core.txt")', self.workflow_text)
        self.assertIn('assert candidate["requirements_sha256"] == digest("package/requirements-linux-core.in")', self.workflow_text)
        self.assertIn("https://apt.airunner.art/pool/main/a/airunner/airunner_6.1.3-3_all.deb", self.workflow_text)
        self.assertIn("60c07b5c2e8701b9f07309ee10be0327b5ef5ae908464fc370619bcfe4e4b87c", self.workflow_text)
        self.assertIn('baseline_version == "6.1.3-3"', self.workflow_text)
        self.assertIn("apt-get install -y \"$baseline_deb\"", self.upgrade_smoke)
        self.assertIn("apt-get remove -y airunner", self.upgrade_smoke)
        self.assertIn("apt-get purge -y airunner", self.upgrade_smoke)
        self.assertIn("core_upgrade_fixture", self.upgrade_smoke)
        self.assertIn(".upgrade-ownership-marker", self.upgrade_smoke)
        self.assertIn('"published_prior_release_upgrade": {', self.upgrade_smoke)
        self.assertIn('"source_revision": candidate["upgrade_baseline"]["source_revision"]', self.upgrade_smoke)
        self.assertIn('[[ -f "$policy" && ! -L "$policy" ]] ||', self.upgrade_smoke)
        self.assertIn('elif (( policy_changed )); then\n    rm -f "$policy"', self.upgrade_smoke)
        self.assertIn('if (( dropin_created )); then rm -f "$dropin"', self.upgrade_smoke)
        self.assertIn('if (( service_start_attempted )); then', self.upgrade_smoke)
        self.assertIn('if (( unit_config_changed )); then systemctl daemon-reload', self.upgrade_smoke)
        self.assertIn('cp -a "$policy" "$policy_backup"\n  had_policy=1', self.upgrade_smoke)
        self.assertLess(
            self.upgrade_smoke.index("airunner is already installed"),
            self.upgrade_smoke.index('key_file=$(mktemp'),
        )
        self.assertIn("_REVISION = \"69fb44e0d99f\"", self.fixture)
        self.assertIn("synthetic_intermediate_alembic_revision", self.fixture)
        self.assertNotIn("contents: write", self.workflow_text)

    def test_refusing_existing_package_does_not_touch_service_or_temp_paths(self):
        with tempfile.TemporaryDirectory(prefix="core-upgrade-refusal-") as temporary:
            tmp_path = Path(temporary)
            artifact = tmp_path / "artifact"
            fake_bin = tmp_path / "bin"
            artifact.mkdir()
            fake_bin.mkdir()
            source_sha = "a" * 40
            deb = artifact / "airunner_6.1.9-1_amd64.deb"
            deb.write_bytes(b"synthetic-test-only-not-a-debian-package")
            baseline = artifact / "airunner_6.1.3-3_all.deb"
            baseline.write_bytes(b"synthetic-test-only-published-baseline")
            database = artifact / "synthetic-upgrade-fixture" / "airunner.db"
            database.parent.mkdir()
            database.write_bytes(b"synthetic-test-database")
            candidate = {
                "source_sha": source_sha,
                "debian_sha256": hashlib.sha256(deb.read_bytes()).hexdigest(),
                "lock_sha256": "b" * 64,
                "upgrade_baseline": {
                    "version": "6.1.3-3",
                    "architecture": "all",
                    "sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                },
            }
            fixture = {
                "source_sha": source_sha,
                "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
                "fixture_kind": "synthetic_intermediate_alembic_revision",
                "fixture_payload": "synthetic-test-payload",
                "alembic_revision_before_upgrade": "69fb44e0d99f",
                "expected_alembic_heads_after_upgrade": ["f3a2c9e4b710"],
            }
            (artifact / "candidate.json").write_text(json.dumps(candidate))
            (database.parent / "fixture.json").write_text(json.dumps(fixture))
            call_log = tmp_path / "calls.log"

            def fake_command(name, body):
                command = fake_bin / name
                command.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
                command.chmod(0o755)

            fake_command("id", 'echo "id $*" >> "$CALL_LOG"; echo 0')
            fake_command(
                "dpkg-query",
                'echo "dpkg-query $*" >> "$CALL_LOG"; echo installed; exit 0',
            )
            fake_command(
                "dpkg-deb",
                '''echo "dpkg-deb $*" >> "$CALL_LOG"
case "$2:$3" in
  */airunner_6.1.3-3_all.deb:Version) echo 6.1.3-3 ;;
  */airunner_6.1.3-3_all.deb:Architecture) echo all ;;
  *:Version) echo 6.1.9-1 ;;
  *:Architecture) echo amd64 ;;
  *) exit 1 ;;
esac''',
            )
            fake_command(
                "mktemp",
                'echo "mktemp $*" >> "$CALL_LOG"; echo "$TEST_TMP/fake-temp"',
            )
            fake_command(
                "systemctl",
                'echo "systemctl $*" >> "$CALL_LOG"; exit 0',
            )
            for name in ("rm", "rmdir", "cp"):
                fake_command(name, f'echo "{name} $*" >> "$CALL_LOG"; exit 0')

            before = {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in artifact.rglob("*")
                if path.is_file()
            }
            environment = os.environ.copy()
            environment.update(
                {
                    "CORE_SOURCE_SHA": source_sha,
                    "CALL_LOG": str(call_log),
                    "TEST_TMP": str(tmp_path),
                    "PATH": f"{fake_bin}{os.pathsep}{environment['PATH']}",
                }
            )
            result = subprocess.run(
                ["bash", str(UPGRADE_SMOKE), str(artifact)],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already installed", result.stderr)
            calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(line.startswith("dpkg-query ") for line in calls))
            self.assertFalse(any(line.startswith("systemctl ") for line in calls))
            self.assertFalse(any(line.startswith("mktemp ") for line in calls))
            self.assertFalse(any(line.startswith(("rm ", "rmdir ", "cp ")) for line in calls))
            after = {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in artifact.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertFalse((artifact / "candidate-upgrade-validation.json").exists())

            # A rejected digest must also exit before temporary allocation,
            # policy changes, systemd reload, or service stop.
            candidate["debian_sha256"] = "0" * 64
            (artifact / "candidate.json").write_text(json.dumps(candidate))
            fake_command(
                "dpkg-query",
                'echo "dpkg-query $*" >> "$CALL_LOG"; echo not-installed; exit 0',
            )
            call_log.write_text("", encoding="utf-8")
            bad_digest_before = {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in artifact.rglob("*")
                if path.is_file()
            }
            bad_digest_result = subprocess.run(
                ["bash", str(UPGRADE_SMOKE), str(artifact)],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(bad_digest_result.returncode, 0)
            bad_digest_calls = call_log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(line.startswith("dpkg-query ") for line in bad_digest_calls))
            self.assertTrue(any(line.startswith("dpkg-deb ") for line in bad_digest_calls))
            self.assertFalse(any(line.startswith("systemctl ") for line in bad_digest_calls))
            self.assertFalse(any(line.startswith("mktemp ") for line in bad_digest_calls))
            self.assertFalse(any(line.startswith(("rm ", "rmdir ", "cp ")) for line in bad_digest_calls))
            bad_digest_after = {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in artifact.rglob("*")
                if path.is_file()
            }
            self.assertEqual(bad_digest_before, bad_digest_after)
            self.assertFalse((artifact / "candidate-upgrade-validation.json").exists())

    def test_fixture_database_hash_matches_after_creator_process_exits(self):
        with tempfile.TemporaryDirectory(prefix="core-upgrade-fixture-") as temporary:
            output = Path(temporary) / "fixture"
            environment = os.environ.copy()
            source_paths = [
                ROOT / "services/src",
                ROOT / "native/src",
                ROOT / "debian/vendor",
            ]
            environment["PYTHONPATH"] = os.pathsep.join(
                [*(str(path) for path in source_paths), environment.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep)
            result = subprocess.run(
                [
                    sys.executable,
                    str(FIXTURE),
                    "--output-dir",
                    str(output),
                    "--source-sha",
                    "b" * 40,
                ],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            record = json.loads((output / "fixture.json").read_text(encoding="utf-8"))
            database = output / "airunner.db"
            actual_digest = hashlib.sha256(database.read_bytes()).hexdigest()
            self.assertEqual(record["database_sha256"], actual_digest)
            self.assertFalse((output / "airunner.db-wal").exists())
            self.assertFalse((output / "airunner.db-shm").exists())


if __name__ == "__main__":
    unittest.main()
