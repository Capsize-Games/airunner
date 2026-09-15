"""Execute a candidate release artifact and verify it behaves, before publishing.

A PyPI version can be yanked but never replaced, so the artifact has to be
proven before upload. 6.1.3 resolved, installed, and then could not start.

This gate is deliberately *behavioural*. It installs through the advertised
top-level request into a clean interpreter outside the source tree and then
runs things. ``check_artifact_imports.py`` is a static companion that explains
*why* a probe failed; it is not a substitute for running the code, and neither
of them proves the application works beyond the probes listed here.

What it does NOT establish: GUI behaviour, model inference, any platform other
than the one it runs on, or any Python version other than the one invoked.

Usage:
    python scripts/artifact_runtime_gate.py --find-links dist --version 6.1.4
    python scripts/artifact_runtime_gate.py --published 6.1.3   # negative control
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

FIRST_PARTY = ("airunner", "airunner_common", "airunner_services")

# (probe id, argv, required). Kept small, bounded, and free of model weights,
# network calls and GPU use.
ENTRY_PROBES = [
    ("headless-help", ["airunner-headless", "--help"], True),
    ("service-help", ["airunner-service", "--help"], True),
    # The daemon is the failure observed in 6.1.3: it imports pygments at
    # module scope via airunner_services.utils.text. It is required because the
    # GUI launcher spawns it during startup.
    ("daemon-help", ["airunner-daemon", "--help"], True),
]

# Importing the daemon's API server is the exact initialisation path that died
# in 6.1.3, and it needs no weights, port bind or GPU.
IMPORT_PROBES = [
    ("import-first-party", [f"import {m}" for m in FIRST_PARTY], True),
    ("init-daemon-api", ["import airunner_services.api.server"], True),
]

TIMEOUT = 300


def run(cmd: list[str], env: dict | None = None, cwd: str | None = None):
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env, cwd=cwd
    )


def clean_env(venv: Path, home: Path) -> dict:
    """A deliberately hostile-to-contamination environment.

    No inherited PYTHONPATH, no user site-packages, HOME redirected away from
    real config and model directories, and Qt forced offscreen.
    """
    return {
        "PATH": f"{venv / 'bin'}:/usr/bin:/bin",
        "HOME": str(home),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "QT_QPA_PLATFORM": "offscreen",
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_CONFIG_HOME": str(home / "config"),
    }


def pypi_has_version(dist: str, version: str) -> bool:
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{dist}/{version}/json", timeout=20
        ):
            return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    except urllib.error.URLError:
        print("  warning: could not reach PyPI to check version collision")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--find-links", type=Path, help="Directory of candidate wheels.")
    ap.add_argument("--version", help="Candidate version to require.")
    ap.add_argument("--published", help="Test an already-published version instead.")
    ap.add_argument("--extras", default="", help="e.g. 'ml'")
    args = ap.parse_args()

    if not args.published and not (args.find_links and args.version):
        ap.error("give --find-links with --version, or --published")

    version = args.published or args.version
    spec = f"airunner[{args.extras}]=={version}" if args.extras else f"airunner=={version}"

    work = Path(tempfile.mkdtemp(prefix="airunner-gate-"))
    venv, home = work / "venv", work / "home"
    home.mkdir()
    # Run outside the source tree so a checkout can never satisfy an import.
    cwd = str(work)

    print(f"gate workdir : {work}")
    print(f"install spec : {spec}")
    print(f"mode         : {'PUBLISHED (control)' if args.published else 'CANDIDATE'}")

    if args.find_links and args.version:
        # If the candidate version already exists upstream, a find-links install
        # cannot be proven to have used the local artifact -- and publishing it
        # would fail anyway.
        if pypi_has_version("airunner", args.version):
            print(
                f"\nFAIL: airunner=={args.version} already exists on PyPI. The candidate "
                "cannot be distinguished from the published artifact, and the "
                "version cannot be published again."
            )
            return 1

    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = [str(venv / "bin" / "pip"), "install", "--disable-pip-version-check"]
    if args.find_links:
        # Advertised top-level request; the resolver pulls the siblings itself.
        # Bulk-installing every wheel would hide a missing dependency edge
        # between the distributions.
        pip += ["--find-links", str(args.find_links.resolve())]
    print("\n--- install ---")
    res = run(pip + [spec])
    if res.returncode != 0:
        print(f"FAIL: install returned {res.returncode}")
        print(res.stdout[-3000:], res.stderr[-3000:])
        return 1
    print("install OK")

    env = clean_env(venv, home)
    py = str(venv / "bin" / "python")

    print("\n--- installed first-party distributions ---")
    listing = run([str(venv / "bin" / "pip"), "list", "--format=json"], env=env)
    installed = {
        d["name"].lower().replace("_", "-"): d["version"]
        for d in json.loads(listing.stdout or "[]")
    }
    for name in ("airunner", "airunner-common", "airunner-services", "airunner-native"):
        print(f"  {name:<20} {installed.get(name, '<NOT INSTALLED>')}")
    if installed.get("airunner") != version:
        print(f"FAIL: expected airunner=={version}, got {installed.get('airunner')}")
        return 1

    print("\n--- provenance: first-party code must come from site-packages ---")
    prov = run([py, "-c", "import airunner;print(airunner.__file__)"], env=env, cwd=cwd)
    print(f"  {prov.stdout.strip() or prov.stderr.strip()[:200]}")
    if "site-packages" not in prov.stdout:
        print("FAIL: airunner did not import from the installed artifact")
        return 1

    results: list[tuple[str, int, bool, str]] = []

    print("\n--- import probes ---")
    for pid, stmts, required in IMPORT_PROBES:
        r = run([py, "-c", "; ".join(stmts)], env=env, cwd=cwd)
        note = ""
        if r.returncode != 0:
            for line in r.stderr.splitlines():
                if "Error" in line:
                    note = line.strip()[:120]
        results.append((pid, r.returncode, required, note))
        print(f"  {pid:<22} rc={r.returncode} {note}")

    print("\n--- entry-point probes ---")
    for pid, argv, required in ENTRY_PROBES:
        exe = venv / "bin" / argv[0]
        if not exe.exists():
            results.append((pid, 127, required, "entry point not installed"))
            print(f"  {pid:<22} rc=127 entry point not installed")
            continue
        r = run([str(exe)] + argv[1:], env=env, cwd=cwd)
        note = ""
        if r.returncode != 0:
            for line in (r.stderr + r.stdout).splitlines():
                if "Error" in line:
                    note = line.strip()[:120]
        results.append((pid, r.returncode, required, note))
        print(f"  {pid:<22} rc={r.returncode} {note}")

    failures = [(p, rc, n) for p, rc, req, n in results if req and rc != 0]
    print("\n" + "=" * 68)
    print(f"probes run: {len(results)}   required failures: {len(failures)}")
    if failures:
        print("\nREQUIRED PROBES FAILED -- do not publish this artifact:")
        for pid, rc, note in failures:
            print(f"  {pid:<22} rc={rc} {note}")
        print(f"\nRun scripts/check_artifact_imports.py inside {venv} to see which")
        print("module-scope imports are unsatisfied.")
        return 1

    print("\nOK: every required probe passed.")
    print("Scope: this proves the probes above, on this platform and interpreter.")
    print("It does not prove GUI behaviour, inference, or other platforms.")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
