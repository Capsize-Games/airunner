"""Verify one prior successful CORE candidate workflow run before promotion."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


WORKFLOW = ".github/workflows/core-debian-candidate.yml"
REQUIRED_JOBS = {
    "build-core-debian-candidate",
    "clean-install-smoke",
    "published-upgrade-data-smoke",
}


class CandidateRunError(ValueError):
    """A prior candidate run does not satisfy release identity requirements."""
    pass


def _get_json(url: str, *, token: str, opener=urlopen):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with opener(request, timeout=15) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        raise CandidateRunError("cannot verify the requested CORE candidate run") from exc


def verify_candidate_run(
    *, repository: str, run_id: int, tag: str, source_sha: str, token: str,
    output_json: Path, output_env: Path | None = None, opener=urlopen,
) -> dict:
    """Verify source-bound run/job/artifact metadata and write its receipt."""
    if repository != "Capsize-Games/airunner" or not token:
        raise CandidateRunError("candidate run verification requires repository authentication")
    if run_id <= 0 or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise CandidateRunError("candidate run ID or version tag is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise CandidateRunError("candidate source identity is invalid")
    api = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
    run = _get_json(api, token=token, opener=opener)
    attempt = _validate_run_identity(
        run, repository=repository, run_id=run_id, tag=tag, source_sha=source_sha
    )
    _require_successful_jobs(api, token=token, opener=opener)
    selected = _require_run_artifacts(
        api, token=token, run_id=run_id, attempt=attempt, opener=opener
    )

    proof = {
        "schema_version": 1,
        "repository": repository,
        "workflow": WORKFLOW,
        "run_id": run_id,
        "run_attempt": attempt,
        "event": run["event"],
        "tag": tag,
        "source_sha": source_sha,
        "run_conclusion": run["conclusion"],
        "required_jobs": sorted(REQUIRED_JOBS),
        "successful_jobs": sorted(REQUIRED_JOBS),
        "artifacts": {
            name: {
                "id": selected[name]["id"],
                "name": name,
                "size_in_bytes": selected[name]["size_in_bytes"],
                "digest": selected[name].get("digest"),
            }
        for name in sorted(selected)
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if output_env is not None:
        with output_env.open("a", encoding="utf-8") as stream:
            stream.write(f"run_id={run_id}\n")
            stream.write(f"run_attempt={attempt}\n")
    return proof


def _validate_run_identity(run, *, repository: str, run_id: int, tag: str, source_sha: str) -> int:
    """Validate workflow path, repository, tag, source commit and success state."""
    if not isinstance(run, dict):
        raise CandidateRunError("candidate run response is invalid")
    run_path = str(run.get("path", "")).split("@", 1)[0]
    run_repo = (run.get("repository") or {}).get("full_name")
    head_repo = (run.get("head_repository") or {}).get("full_name")
    attempt = run.get("run_attempt")
    valid = (
        run.get("id") == run_id and run_path == WORKFLOW
        and run_repo == repository and head_repo == repository
        and run.get("event") == "workflow_dispatch" and run.get("head_branch") == tag
        and run.get("head_sha") == source_sha and run.get("status") == "completed"
        and run.get("conclusion") == "success" and isinstance(attempt, int)
        and not isinstance(attempt, bool) and attempt > 0
    )
    if not valid:
        raise CandidateRunError("candidate run is not a successful exact-tag CORE workflow run")
    return attempt


def _require_successful_jobs(api: str, *, token: str, opener) -> None:
    """Require the build, clean-install and upgrade jobs to have succeeded."""
    payload = _get_json(f"{api}/jobs?filter=latest&per_page=100", token=token, opener=opener)
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        raise CandidateRunError("candidate run jobs response is invalid")
    successful = {
        job.get("name") for job in jobs
        if job.get("status") == "completed" and job.get("conclusion") == "success"
    }
    if not REQUIRED_JOBS <= successful:
        raise CandidateRunError("candidate run lacks a successful build, clean-install, or upgrade job")


def _require_run_artifacts(api: str, *, token: str, run_id: int, attempt: int, opener) -> dict:
    """Require all attempt-specific, unexpired artifacts from that workflow run."""
    payload = _get_json(f"{api}/artifacts?per_page=100", token=token, opener=opener)
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(artifacts, list):
        raise CandidateRunError("candidate run artifacts response is invalid")
    expected_names = {
        f"core-debian-candidate-{run_id}-{attempt}",
        f"core-debian-validation-{run_id}-{attempt}",
        f"core-debian-upgrade-validation-{run_id}-{attempt}",
    }
    selected = {
        artifact.get("name"): artifact for artifact in artifacts
        if isinstance(artifact, dict) and artifact.get("name") in expected_names
    }
    valid = set(selected) == expected_names
    valid = valid and all(
        artifact.get("expired") is False
        and isinstance(artifact.get("id"), int)
        and not isinstance(artifact.get("id"), bool)
        and isinstance(artifact.get("size_in_bytes"), int)
        and artifact["size_in_bytes"] > 0
        for artifact in selected.values()
    )
    if not valid:
        raise CandidateRunError("candidate run does not retain all three exact-attempt artifacts")
    return selected


def main() -> int:
    """Verify the requested candidate run from command-line arguments."""
    """Validate one prior CORE run and emit a promotion-time JSON receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-env", type=Path)
    args = parser.parse_args()
    try:
        verify_candidate_run(
            repository=args.repository,
            run_id=args.run_id,
            tag=args.tag,
            source_sha=args.source_sha,
            token=os.environ.get("GITHUB_TOKEN", ""),
            output_json=args.output_json,
            output_env=args.output_env,
        )
    except CandidateRunError as exc:
        print(f"candidate run verification failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
