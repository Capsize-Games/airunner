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
import ast
import json
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

# Deferring an import past argparse can make --help succeed while the
# application is still broken, so --help alone proves very little. This probe
# runs a documented operation that constructs real objects and writes a file,
# entirely within the test-owned HOME: no port bind, no weights, no GPU.
BASE_OPERATION = ("daemon-generate-config", ["airunner-daemon", "--generate-config"])

# The optional-ML capability boundary. The CORE daemon is expected to start
# without torch; this probe builds the production API with its real default
# registry and exercises the capability handler without starting a sidecar.
OPTIONAL_BOUNDARY_SRC = """
import asyncio, importlib.util, sys
from starlette.requests import Request
if importlib.util.find_spec("torch") is not None:
    sys.exit(2)                      # ML present: absent-runtime case not tested

from airunner_services.api.server import create_app
from airunner_services.api.routes import llm_local_routes
api = create_app(enable_cors=False)
request = Request({
    "type": "http", "method": "GET", "path": "/api/v1/llm/local-inference",
    "headers": [], "query_string": b"", "server": ("candidate", 80),
    "client": ("probe", 1), "scheme": "http",
})
request.scope["app"] = api
try:
    result = asyncio.run(llm_local_routes.local_inference_capability(request))
except Exception as exc:
    print(f"capability handler failed: {type(exc).__name__}: {exc}")
    sys.exit(5)
if result.runtime.status not in {"unavailable", "stopped"}:
    print(f"expected unavailable/stopped runtime, got {result.runtime.status!r}")
    sys.exit(4)
if any(model.loaded for model in result.models):
    print("capability claimed a model was loaded without a runtime")
    sys.exit(4)
if result.contract != "airunner.local-inference" or result.contract_version != "1":
    print("capability contract identity is missing or unexpected")
    sys.exit(4)
sys.exit(0)
"""

TIMEOUT = 300

# The publish workflow accepts a package selection so the sibling projects can
# be created before `airunner` itself pins them (the first-publish bootstrap).
# That selection must never be able to reach Publish without validation: a
# skipped gate is not a passed gate.
ALLOWED_PACKAGE_TOKENS = frozenset({"services", "native", "."})

# Distribution that each build directory produces, for reporting.
TOKEN_DISTRIBUTION = {
    "services": "airunner-services",
    "native": "airunner-native",
    ".": "airunner",
}


def release_version_from_setup(path: Path) -> str:
    """Read a package's literal release version without importing setup.py.

    Build helpers often import setuptools, which is intentionally installed in
    isolated build environments and may not exist in the CI source-gate
    interpreter. Parsing the single literal also avoids executing packaging
    code during a metadata consistency check.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "_RELEASE_VERSION"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{path}: _RELEASE_VERSION must be a non-empty string"
            )
        return value
    raise ValueError(f"{path}: _RELEASE_VERSION assignment not found")


# airunner-common is independently versioned and published from its own
# repository. Only these distributions are built from the candidate here.
CANDIDATE_DISTRIBUTIONS = frozenset(
    {"airunner", "airunner-services", "airunner-native"}
)


def optional_boundary_is_failure(
    returncode: int, require_boundary: bool
) -> bool:
    """Return True when the no-ML capability probe rc fails the gate.

    rc=0 always passes (unavailable capability is explicit). rc=2 means
    torch was present so the absent-runtime case was skipped: it fails
    only with ``--require-optional-boundary``. Any other rc fails.
    """
    if returncode == 0:
        return False
    if returncode == 2:
        return require_boundary
    return True


class UnsupportedSelection(ValueError):
    """The requested package selection cannot be validated by this gate."""


def plan_validation(selection: str) -> tuple[str, str]:
    """Decide what to install for a given package selection.

    Returns ``(mode, top_level_distribution)``. Raises UnsupportedSelection
    rather than returning something un-validatable, so the caller fails before
    Publish instead of skipping.

    Exact-token matching, not a substring test: `contains(selection, '.')` would
    also be true for a token like ``./services`` or ``x.y`` and would classify
    it as a full release.
    """
    tokens = selection.split()
    if not tokens:
        raise UnsupportedSelection("empty package selection")
    unknown = sorted({t for t in tokens if t not in ALLOWED_PACKAGE_TOKENS})
    if unknown:
        raise UnsupportedSelection(
            f"unknown package selection token(s): {', '.join(unknown)}; "
            f"allowed: {', '.join(sorted(ALLOWED_PACKAGE_TOKENS))}"
        )
    if "." in tokens:
        # The full surface. Installing `airunner` exercises the sibling edges.
        return ("full", "airunner")
    if "services" in tokens:
        # Sibling-only bootstrap. `airunner` is not being published, but
        # airunner-services owns the daemon entry points -- and the console
        # scripts are where the 6.1.3 failure actually surfaced -- so this
        # profile is validatable on its own terms.
        return ("services", "airunner-services")
    raise UnsupportedSelection(
        f"selection {selection!r} publishes only "
        f"{', '.join(TOKEN_DISTRIBUTION[t] for t in tokens)}, which this gate "
        "cannot execute (no console scripts or importable runtime surface). "
        "Publish it deliberately with a documented reason, or add validation "
        "for it -- do not skip the gate."
    )



def run(cmd: list[str], env: dict | None = None, cwd: str | None = None):
    # check=False on purpose: a failing probe IS the signal here.
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        env=env,
        cwd=cwd,
        check=False,
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


def locked_dependency_install_command(
    pip: Path, requirements: Path, wheelhouse: Path
) -> list[str]:
    """Install the complete reviewed runtime closure without index access."""
    return [
        str(pip),
        "install",
        "--isolated",
        "--no-cache-dir",
        "--disable-pip-version-check",
        "--no-index",
        "--find-links",
        str(wheelhouse.resolve()),
        "--require-hashes",
        "--only-binary=:all:",
        "-r",
        str(requirements.resolve()),
    ]


def local_candidate_install_command(
    pip: Path, candidate_dir: Path, report_path: Path, spec: str
) -> list[str]:
    """Install only the built first-party artifact from its local directory."""
    return [
        str(pip),
        "install",
        "--isolated",
        "--no-cache-dir",
        "--disable-pip-version-check",
        "--no-index",
        "--find-links",
        str(candidate_dir.resolve()),
        "--no-deps",
        "--force-reinstall",
        "--report",
        str(report_path),
        spec,
    ]


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
    except urllib.error.URLError as exc:
        # Not reachable is not the same as not present. Treating it as absent
        # would let a release proceed on an unchecked precondition.
        raise RuntimeError(
            f"could not reach PyPI to check whether {dist}=={version} already "
            f"exists ({exc}). Refusing to treat that as 'absent'."
        ) from exc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--find-links", type=Path, help="Directory of candidate wheels.")
    ap.add_argument("--version", help="Candidate version to require.")
    ap.add_argument("--published", help="Test an already-published version instead.")
    ap.add_argument(
        "--locked-dependency-requirements",
        type=Path,
        help="Hash-locked runtime requirements staged in a local wheelhouse.",
    )
    ap.add_argument(
        "--locked-dependency-wheelhouse",
        type=Path,
        help="Local wheelhouse matching --locked-dependency-requirements.",
    )
    ap.add_argument("--extras", default="", help="e.g. 'ml'")
    ap.add_argument(
        "--packages",
        default=".",
        help=(
            "The publish workflow's package selection, validated exactly. "
            "Determines which distribution is installed and exercised."
        ),
    )
    ap.add_argument(
        "--require-optional-boundary",
        action="store_true",
        help=(
            "Fail when the no-ML capability probe is skipped "
            "(rc=2, torch present). Release candidates must exercise "
            "the unavailable-runtime capability contract."
        ),
    )
    args = ap.parse_args()

    if bool(args.locked_dependency_requirements) != bool(
        args.locked_dependency_wheelhouse
    ):
        ap.error(
            "--locked-dependency-requirements and "
            "--locked-dependency-wheelhouse must be supplied together"
        )
    if args.locked_dependency_requirements and args.published:
        ap.error("locked candidate dependencies are only supported for candidate mode")

    if not args.published and not (args.find_links and args.version):
        ap.error("give --find-links with --version, or --published")

    version = args.published or args.version
    try:
        mode, top_level = plan_validation(args.packages)
    except UnsupportedSelection as exc:
        print(f"FAIL: {exc}")
        return 1
    spec = f"{top_level}=={version}"
    if args.extras:
        spec = f"{top_level}[{args.extras}]=={version}"

    work = Path(tempfile.mkdtemp(prefix="airunner-gate-"))
    venv, home = work / "venv", work / "home"
    home.mkdir()
    # Run outside the source tree so a checkout can never satisfy an import.
    cwd = str(work)

    print(f"gate workdir : {work}")
    print(f"selection    : {args.packages!r} -> mode={mode}, top-level={top_level}")
    print(f"install spec : {spec}")
    print(f"mode         : {'PUBLISHED (control)' if args.published else 'CANDIDATE'}")

    # If the candidate version already exists upstream, a find-links install
    # cannot be proven to have used the local artifact -- and that version
    # could not be published again anyway. --published skips this deliberately,
    # so a known-published artifact can still be re-tested for diagnostics.
    if args.find_links and args.version and pypi_has_version(top_level, args.version):
        print(
            f"\nFAIL: {top_level}=={args.version} already exists on PyPI. The "
            "candidate cannot be distinguished from the published artifact, "
            "and that version cannot be published again."
        )
        return 1

    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    # --isolated ignores user/global pip config and PIP_* env vars, so a stray
    # index-url or find-links on the machine cannot change what gets installed.
    report_path = work / "install-report.json"
    pip = venv / "bin" / "pip"
    if args.locked_dependency_requirements:
        print("\n--- install hash-locked runtime dependencies ---")
        runtime_install = locked_dependency_install_command(
            pip,
            args.locked_dependency_requirements,
            args.locked_dependency_wheelhouse,
        )
        res = run(runtime_install)
        if res.returncode != 0:
            print(f"FAIL: runtime dependency install returned {res.returncode}")
            print(res.stdout[-3000:], res.stderr[-3000:])
            return 1
        print("locked runtime dependencies installed")
        candidate_install = local_candidate_install_command(
            pip, args.find_links, report_path, spec
        )
    else:
        # Compatibility path for explicit diagnostic use outside reviewed CI.
        # Release workflows pass the locked arguments above.
        candidate_install = [
            str(pip),
            "install",
            "--isolated",
            "--no-cache-dir",
            "--disable-pip-version-check",
        ]
        if args.find_links:
            candidate_install += ["--find-links", str(args.find_links.resolve())]
        candidate_install += ["--report", str(report_path), spec]

    print("\n--- install candidate distribution ---")
    res = run(candidate_install)
    if res.returncode != 0:
        print(f"FAIL: install returned {res.returncode}")
        print(res.stdout[-3000:], res.stderr[-3000:])
        return 1
    print("install OK")

    if args.locked_dependency_requirements:
        print("\n--- validate locked candidate environment ---")
        check = run([str(pip), "check"])
        if check.returncode != 0:
            print(f"FAIL: pip check returned {check.returncode}")
            print(check.stdout[-3000:], check.stderr[-3000:])
            return 1
        print(check.stdout.strip() or "pip check passed")

    # Provenance. Matching version numbers is necessary but not sufficient: a
    # same-version first-party wheel could still have come from the index.
    # pip's installation report records, per distribution, the URL it actually
    # resolved and the hash of the archive it used.
    if args.find_links:
        print("\n--- candidate provenance (pip installation report) ---")
        try:
            report = json.loads(report_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL: could not read pip's installation report: {exc}")
            return 1
        candidate_dir = args.find_links.resolve()
        bad: list[str] = []
        seen = 0
        for item in report.get("install", []):
            meta = item.get("metadata", {})
            name = (meta.get("name") or "").lower().replace("_", "-")
            if name not in CANDIDATE_DISTRIBUTIONS:
                continue
            seen += 1
            info = item.get("download_info", {}) or {}
            url = info.get("url", "")
            digest = (
                (info.get("archive_info", {}) or {}).get("hashes", {}) or {}
            ).get("sha256", "")
            local = url.startswith("file://") and str(candidate_dir) in url
            print(
                f"  {name:<20} {meta.get('version','?'):<14} "
                f"{'candidate-dir' if local else 'NOT FROM CANDIDATE DIR'} "
                f"sha256={digest[:16] or '<none>'}"
            )
            if not local:
                bad.append(f"{name} resolved from {url or '<unknown origin>'}")
        if not seen:
            print("FAIL: installation report lists no first-party distributions")
            return 1
        if bad:
            print(
                "\nFAIL: first-party artifacts did not come from the candidate "
                "directory -- a published wheel may have been substituted:"
            )
            for line in bad:
                print(f"  {line}")
            return 1

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

    # Every distribution built by this repository that got installed must be
    # the candidate. airunner-common is independently versioned and is expected
    # to resolve from PyPI; the remaining packages pin one another by VERSION.
    wrong = {
        n: v
        for n, v in installed.items()
        if n in CANDIDATE_DISTRIBUTIONS and v != version
    }
    if wrong:
        print(f"FAIL: first-party distributions are not the candidate {version}:")
        for n, v in sorted(wrong.items()):
            print(f"  {n} == {v}  (expected {version})")
        return 1
    if installed.get(top_level) != version:
        print(f"FAIL: expected {top_level}=={version}, got {installed.get(top_level)}")
        return 1

    # airunner-native is a SEPARATE installation profile, not a missing edge.
    # It ships the `airunner-native` launcher and depends on common+services;
    # the GUI command is owned by the `airunner` distribution (issue #2042), so
    # `pip install airunner` deliberately does not pull it. Recorded, not added:
    # installing it here would hide whatever the real contract turns out to be.
    if "airunner-native" not in installed:
        print("  note: airunner-native absent -- separate profile, not required here")

    print("\n--- provenance: first-party code must come from site-packages ---")
    probe_module = top_level.replace("-", "_")
    prov = run(
        [py, "-c", f"import {probe_module};print({probe_module}.__file__)"],
        env=env,
        cwd=cwd,
    )
    print(f"  {prov.stdout.strip() or prov.stderr.strip()[:200]}")
    if "site-packages" not in prov.stdout:
        print(f"FAIL: {probe_module} did not import from the installed artifact")
        return 1

    results: list[tuple[str, int, bool, str]] = []

    import_probes = IMPORT_PROBES
    if mode == "services":
        # `airunner` (the GUI distribution) is not part of this selection.
        import_probes = [
            (pid, [st for st in stmts if st != "import airunner"], req)
            for pid, stmts, req in IMPORT_PROBES
        ]

    print("\n--- import probes ---")
    for pid, stmts, required in import_probes:
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

    print("\n--- base operation (beyond argument parsing) ---")
    pid, argv = BASE_OPERATION
    exe = venv / "bin" / argv[0]
    r = run([str(exe)] + argv[1:], env=env, cwd=cwd)
    produced = list((home / ".local").rglob("daemon.yaml")) if (home / ".local").exists() else []
    ok = r.returncode == 0 and bool(produced)
    note = "" if ok else (r.stderr or r.stdout).strip().splitlines()[-1][:120] if (r.stderr or r.stdout) else "no config written"
    results.append((pid, 0 if ok else (r.returncode or 1), True, note))
    print(f"  {pid:<22} rc={r.returncode} config_written={bool(produced)} {note}")

    print("\n--- no-ML capability (model runtime must report unavailable) ---")
    rb = run([py, "-c", OPTIONAL_BOUNDARY_SRC], env=env, cwd=cwd)
    meaning = {
        0: ("pass", "production capability reports unavailable and no model loaded"),
        2: ("skip", "torch present -- CORE no-ML case not exercised"),
        4: ("FAIL", "capability contract or loaded-state assertion failed"),
        5: ("FAIL", "capability handler raised unexpectedly"),
    }.get(rb.returncode, ("FAIL", f"unexpected rc={rb.returncode}"))
    print(f"  no-ml-capability      {meaning[0]}: {meaning[1]}")
    if optional_boundary_is_failure(
        rb.returncode, args.require_optional_boundary
    ):
        note = meaning[1]
        if rb.returncode == 2:
            note += " (run the gate in the CORE profile without torch)"
        results.append(("no-ml-capability", rb.returncode, True, note))

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
