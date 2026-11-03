from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/eval-tests.yml"


def _job_text(text: str, job_name: str, next_job: str) -> str:
    start = text.index(f"  {job_name}:")
    end = text.index(f"  {next_job}:", start)
    return text[start:end]


def _step_text(job: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    start = job.index(marker)
    next_step = job.find("      - name: ", start + len(marker))
    return job[start:] if next_step < 0 else job[start:next_step]


class RuntimeContractDiskWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.contract = _job_text(cls.workflow, "runtime-contract-tests", "runtime-smoke")
        cls.smoke = _job_text(cls.workflow, "runtime-smoke", "packaging-gates")

    def test_contract_reclaims_only_the_existing_sdk_allowlist_before_staging(self) -> None:
        contract_cleanup = _step_text(self.contract, "Reclaim unused hosted-runner SDK space")
        smoke_cleanup = _step_text(self.smoke, "Reclaim unused hosted-runner SDK space")
        expected = [
            "/usr/share/dotnet",
            "/usr/local/lib/android",
            "/opt/ghc",
            "/usr/local/share/boost",
            "/opt/hostedtoolcache/CodeQL",
        ]
        for path in expected:
            self.assertIn(path, contract_cleanup)
            self.assertIn(path, smoke_cleanup)
        sdk_block = contract_cleanup.split("sudo rm -rf -- \\\n", 1)[1].split("\n          sudo apt-get clean", 1)[0]
        observed = [
            line.strip().rstrip("\\").strip()
            for line in sdk_block.splitlines()
            if line.strip()
        ]
        self.assertEqual(observed, expected)
        self.assertEqual(contract_cleanup.count("sudo rm -rf --"), 2)
        self.assertIn("sudo apt-get clean", contract_cleanup)
        self.assertIn("sudo rm -rf -- /var/lib/apt/lists/*", contract_cleanup)
        self.assertLess(
            self.contract.index("- name: Reclaim unused hosted-runner SDK space"),
            self.contract.index("- name: Install Python dependencies"),
        )

    def test_wheelhouse_is_removed_only_after_hashed_install_and_receipt_copy(self) -> None:
        install = _step_text(self.contract, "Install Python dependencies")
        self.assertIn("--require-hashes -r \"$wheelhouse/requirements.txt\"", install)
        self.assertIn("cp \"$wheelhouse/requirements.txt\" \"$audit/runtime-requirements.txt\"", install)
        self.assertIn("cp \"$wheelhouse/staging-receipt.json\" \"$audit/runtime-staging-receipt.json\"", install)
        self.assertLess(install.index("--require-hashes -r \"$wheelhouse/requirements.txt\""), install.index('rm -rf -- "$wheelhouse"'))
        self.assertIn('python -m pip install --no-index --find-links "$tools"', install)
        self.assertIn("--no-deps --require-hashes -r \"$tools/requirements.txt\"", install)
        self.assertIn("python -m pip check", install)
        self.assertIn("-e './services[linux-release]'", install)

    def test_capacity_failure_evidence_is_written_and_uploaded_always(self) -> None:
        install = _step_text(self.contract, "Install Python dependencies")
        self.assertIn("capacity-before-staging.txt", install)
        self.assertIn("capacity-after-runtime-wheelhouse.txt", install)
        self.assertIn("capacity-after-runtime-install-wheelhouse-cleanup.txt", install)
        self.assertIn("capacity-at-install-exit.txt", install)
        upload = _step_text(self.contract, "Upload runtime input and capacity audit")
        self.assertIn("if: always()", upload)
        self.assertIn("runtime-contract-input-audit", upload)


if __name__ == "__main__":
    unittest.main()
