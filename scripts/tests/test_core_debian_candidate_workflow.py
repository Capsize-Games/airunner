"""Static contract checks for the isolated CORE Debian candidate workflow."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/core-debian-candidate.yml"
SMOKE = ROOT / "scripts/core_debian_candidate_smoke.sh"


class CoreDebianCandidateWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow_text = WORKFLOW.read_text(encoding="utf-8")
        # BaseLoader preserves GitHub's `on` key as a string.
        cls.workflow = yaml.load(cls.workflow_text, Loader=yaml.BaseLoader)
        cls.smoke = SMOKE.read_text(encoding="utf-8")

    def test_has_only_candidate_triggers_and_read_only_permissions(self):
        self.assertEqual(set(self.workflow["on"]), {"workflow_dispatch", "pull_request"})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertIn("github.event_name == 'pull_request' || github.ref_type == 'branch'", self.workflow_text)

    def test_checks_out_exact_candidate_without_persisting_credentials(self):
        self.assertEqual(self.workflow_text.count("persist-credentials: false"), 2)
        self.assertEqual(self.workflow_text.count("ref: ${{ github.event.pull_request.head.sha || github.sha }}"), 2)
        self.assertIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", self.workflow_text)

    def test_every_action_uses_a_full_commit_pin(self):
        for line in self.workflow_text.splitlines():
            if "uses:" in line:
                reference = line.split("uses:", 1)[1].strip()
                self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}(?:\s+# v[0-9]+)?$")

    def test_reviews_inputs_before_binary_only_locked_install(self):
        self.assertIn("--mode verify-record", self.workflow_text)
        self.assertIn("--mode activate", self.workflow_text)
        self.assertIn("pip install --require-hashes --only-binary=:all:", self.workflow_text)
        self.assertIn("-r package/constraints-linux-core.txt", self.workflow_text)
        self.assertIn("pip install --no-deps --no-build-isolation ./services", self.workflow_text)
        self.assertIn("dpkg-buildpackage --build=binary --no-sign", self.workflow_text)

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
            "http://127.0.0.1:8080/health/daemon",
            "Authorization: Bearer $api_key",
            "expected 401",
            "assert_stopped",
            "HF_HUB_OFFLINE=1",
            "AIRUNNER_RUNTIME_BIND_HOST=127.0.0.1",
        ):
            self.assertIn(expected, self.smoke)
        self.assertIn('"real model inference and model downloads"', self.smoke)
        self.assertIn('"offline network-denial behavior"', self.smoke)
        self.assertIn('"upgrade preservation from a prior package"', self.smoke)
        self.assertIn('"APT repository promotion or signing"', self.smoke)
        self.assertIn('"full-ML candidate build"', self.smoke)


if __name__ == "__main__":
    unittest.main()
