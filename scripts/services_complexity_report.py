#!/usr/bin/env python
"""Generate Radon and Xenon complexity reports for services code."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from radon.complexity import cc_rank, cc_visit
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze


DEFAULT_ROOT = Path("server/src/airunner_services")
DEFAULT_OUTPUT = Path("build/services_complexity")
DEFAULT_EXCLUDES = ("build", "dist", "vendor", "__pycache__")
RANKS = "ABCDEF"


@dataclass(frozen=True)
class Thresholds:
    """Thresholds for size and complexity findings."""

    max_file_lines: int = 250
    max_class_lines: int = 250
    max_function_lines: int = 20
    max_complexity_rank: str = "B"
    min_mi: float = 65.0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Report complexity hotspots in services code.",
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDES))
    parser.add_argument("--max-file-lines", type=int, default=250)
    parser.add_argument("--max-class-lines", type=int, default=250)
    parser.add_argument("--max-function-lines", type=int, default=20)
    parser.add_argument("--max-complexity-rank", default="B")
    parser.add_argument("--min-mi", type=float, default=65.0)
    parser.add_argument("--xenon-max-average")
    parser.add_argument("--xenon-max-modules")
    return parser.parse_args()


def split_csv(value: str) -> tuple[str, ...]:
    """Split a comma-separated option into a tuple."""
    return tuple(item.strip() for item in value.split(",") if item.strip())


def is_excluded(path: Path, root: Path, excludes: tuple[str, ...]) -> bool:
    """Return whether the path lives under an excluded directory."""
    parts = path.relative_to(root).parts[:-1]
    return any(part in excludes for part in parts)


def iter_python_files(root: Path, excludes: tuple[str, ...]) -> Iterable[Path]:
    """Yield Python files below the selected root."""
    for path in sorted(root.rglob("*.py")):
        if is_excluded(path, root, excludes):
            continue
        yield path


def docstring_span(node: ast.AST) -> tuple[int, int] | None:
    """Return the start and end line numbers of the node docstring."""
    if not getattr(node, "body", None):
        return None
    first = node.body[0]
    if not isinstance(first, ast.Expr):
        return None
    value = getattr(first, "value", None)
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return None
    return first.lineno, first.end_lineno or first.lineno


def count_code_lines(node: ast.AST, lines: list[str]) -> int:
    """Count non-empty, non-comment code lines in a node."""
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return 0
    skipped = docstring_span(node)
    ignored = set(range(skipped[0], skipped[1] + 1)) if skipped else set()
    count = 0
    for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
        text = lines[lineno - 1].strip()
        if lineno in ignored or not text or text.startswith("#"):
            continue
        count += 1
    return count


def rank_exceeds(rank: str, ceiling: str) -> bool:
    """Return whether the rank exceeds the configured ceiling."""
    return RANKS.index(rank) > RANKS.index(ceiling)


def build_block_entries(source: str) -> tuple[list[dict[str, Any]], dict]:
    """Build Radon block metrics and a lookup index."""
    entries: list[dict[str, Any]] = []
    index: dict[tuple[str, int], dict[str, Any]] = {}
    for block in cc_visit(source):
        entry = {
            "name": block.name,
            "fullname": block.fullname,
            "lineno": block.lineno,
            "endline": block.endline,
            "complexity": block.complexity,
            "rank": cc_rank(block.complexity),
        }
        entries.append(entry)
        index[(block.name, block.lineno)] = entry
    return entries, index


def collect_size_entries(
    tree: ast.AST,
    lines: list[str],
    block_index: dict[tuple[str, int], dict[str, Any]],
    limit: int,
    kinds: tuple[type[ast.AST], ...],
) -> list[dict[str, Any]]:
    """Collect function or class nodes that exceed the size limit."""
    entries: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, kinds):
            continue
        line_count = count_code_lines(node, lines)
        if line_count <= limit:
            continue
        block = block_index.get((node.name, node.lineno), {})
        entries.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "endline": node.end_lineno,
                "line_count": line_count,
                "complexity": block.get("complexity"),
                "rank": block.get("rank"),
            }
        )
    return sorted(entries, key=lambda item: (-item["line_count"], item["lineno"]))


def syntax_error_report(path: Path, root: Path, exc: SyntaxError) -> dict[str, Any]:
    """Return a report entry for a file that failed to parse."""
    return {
        "path": path.relative_to(root).as_posix(),
        "syntax_error": f"{exc.msg} at line {exc.lineno}",
        "file_lines": 0,
        "sloc": 0,
        "lloc": 0,
        "mi": 0.0,
        "long_functions": [],
        "long_classes": [],
        "complex_blocks": [],
    }


def build_file_report(
    path: Path,
    root: Path,
    thresholds: Thresholds,
) -> dict[str, Any]:
    """Analyze one Python file and return its report entry."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return syntax_error_report(path, root, exc)
    blocks, block_index = build_block_entries(source)
    raw_metrics = analyze(source)
    lines = source.splitlines()
    halstead = h_visit(source).total
    mi_score = round(mi_visit(source, multi=True), 2)
    complex_blocks = [
        block for block in blocks if rank_exceeds(block["rank"], thresholds.max_complexity_rank)
    ]
    return {
        "path": path.relative_to(root).as_posix(),
        "file_lines": raw_metrics.sloc,
        "sloc": raw_metrics.sloc,
        "lloc": raw_metrics.lloc,
        "comments": raw_metrics.comments,
        "blank": raw_metrics.blank,
        "mi": mi_score,
        "halstead_volume": round(halstead.volume, 2),
        "max_complexity": max((block["complexity"] for block in blocks), default=0),
        "max_rank": max((block["rank"] for block in blocks), default="A"),
        "long_functions": collect_size_entries(
            tree,
            lines,
            block_index,
            thresholds.max_function_lines,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ),
        "long_classes": collect_size_entries(
            tree,
            lines,
            block_index,
            thresholds.max_class_lines,
            (ast.ClassDef,),
        ),
        "complex_blocks": complex_blocks,
    }


def report_score(report: dict[str, Any], thresholds: Thresholds) -> int:
    """Calculate a simple hotspot score for one file report."""
    score = len(report["long_functions"]) * 3 + len(report["long_classes"]) * 4
    score += len(report["complex_blocks"]) * 2
    score += 1 if report["file_lines"] > thresholds.max_file_lines else 0
    score += 1 if report["mi"] < thresholds.min_mi else 0
    return score


def summarize_reports(
    reports: list[dict[str, Any]],
    thresholds: Thresholds,
) -> dict[str, Any]:
    """Summarize the report collection."""
    return {
        "files_analyzed": len(reports),
        "files_over_limit": sum(report["file_lines"] > thresholds.max_file_lines for report in reports),
        "long_functions": sum(len(report["long_functions"]) for report in reports),
        "long_classes": sum(len(report["long_classes"]) for report in reports),
        "complex_blocks": sum(len(report["complex_blocks"]) for report in reports),
        "low_mi_files": sum(report["mi"] < thresholds.min_mi for report in reports),
        "hotspot_files": sum(report_score(report, thresholds) > 0 for report in reports),
    }


def area_key(path: str) -> str:
    """Group reports into broad services subsystems."""
    parts = Path(path).parts
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0] if parts else path


def issue_reasons(report: dict[str, Any], thresholds: Thresholds) -> list[str]:
    """Return human-readable reasons for a hotspot file."""
    reasons: list[str] = []
    if report["file_lines"] > thresholds.max_file_lines:
        reasons.append(f"{report['file_lines']} SLOC (> {thresholds.max_file_lines})")
    if report["long_functions"]:
        reasons.append(f"{len(report['long_functions'])} function(s) > {thresholds.max_function_lines} lines")
    if report["long_classes"]:
        reasons.append(f"{len(report['long_classes'])} class(es) > {thresholds.max_class_lines} lines")
    if report["complex_blocks"]:
        reasons.append(f"{len(report['complex_blocks'])} block(s) above rank {thresholds.max_complexity_rank}")
    if report["mi"] < thresholds.min_mi:
        reasons.append(f"maintainability index {report['mi']} (< {thresholds.min_mi})")
    return reasons


def build_issue_candidate(
    area: str,
    reports: list[dict[str, Any]],
    thresholds: Thresholds,
) -> dict[str, Any]:
    """Build one draft GitHub issue candidate."""
    area_score = sum(report_score(report, thresholds) for report in reports)
    top_reports = sorted(reports, key=lambda item: -report_score(item, thresholds))[:5]
    lines = [
        "## Why",
        f"The `{area}` area exceeds the current services complexity targets.",
        "",
        "## Targets",
        f"- files: <= {thresholds.max_file_lines} SLOC",
        f"- classes: <= {thresholds.max_class_lines} lines",
        f"- functions: <= {thresholds.max_function_lines} lines",
        f"- Radon block rank: <= {thresholds.max_complexity_rank}",
        f"- maintainability index: >= {thresholds.min_mi}",
        "",
        "## Hotspots",
    ]
    for report in top_reports:
        reasons = "; ".join(issue_reasons(report, thresholds))
        lines.append(f"- `{report['path']}`: {reasons}")
    return {
        "area": area,
        "score": area_score,
        "title": f"Refactor: Reduce services complexity in {area}",
        "body_markdown": "\n".join(lines),
        "files": [report["path"] for report in top_reports],
    }


def build_issue_candidates(
    reports: list[dict[str, Any]],
    thresholds: Thresholds,
) -> list[dict[str, Any]]:
    """Group hotspot files into draft issue candidates."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        if report_score(report, thresholds) == 0:
            continue
        grouped[area_key(report["path"])] += [report]
    candidates = [
        build_issue_candidate(area, area_reports, thresholds)
        for area, area_reports in grouped.items()
    ]
    candidates.sort(key=lambda item: (-item["score"], item["title"]))
    return candidates[:12]


def filter_xenon_output(text: str) -> str:
    """Strip noisy dependency warnings from Xenon output."""
    lines = [line for line in text.splitlines() if "RequestsDependencyWarning" not in line]
    return "\n".join(line for line in lines if line.strip())


def run_xenon(
    root: Path,
    excludes: tuple[str, ...],
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Run Xenon as a best-effort gate over the selected root."""
    max_average = args.xenon_max_average or args.max_complexity_rank
    max_modules = args.xenon_max_modules or args.max_complexity_rank
    command = [
        str(Path(sys.executable).with_name("xenon")),
        "--paths-in-front",
        "--max-average",
        max_average,
        "--max-modules",
        max_modules,
        "--max-absolute",
        args.max_complexity_rank,
        "--exclude",
        ",".join(excludes),
        str(root),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    output = filter_xenon_output(result.stdout + "\n" + result.stderr)
    return {"passed": result.returncode == 0, "output": output.strip()}


def build_markdown(payload: dict[str, Any]) -> str:
    """Render a concise Markdown summary beside the JSON report."""
    summary = payload["summary"]
    thresholds = Thresholds(**payload["thresholds"])
    lines = [
        "# Services Complexity Report",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Root: `{payload['root']}`",
        f"- Files analyzed: {summary['files_analyzed']}",
        f"- Hotspot files: {summary['hotspot_files']}",
        f"- Long functions: {summary['long_functions']}",
        f"- Long classes: {summary['long_classes']}",
        f"- Complex blocks: {summary['complex_blocks']}",
        "",
        "## Top Hotspots",
    ]
    for report in payload["file_reports"][:10]:
        reasons = "; ".join(issue_reasons(report, thresholds))
        if reasons:
            lines.append(f"- `{report['path']}`: {reasons}")
    lines += ["", "## Draft Issue Titles"]
    lines += [f"- {item['title']}" for item in payload["issue_candidates"]]
    lines += ["", "## Xenon Gate", payload["xenon"]["output"] or "No Xenon findings."]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write JSON and Markdown reports to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "services_complexity_report.json"
    md_path = output_dir / "services_complexity_report.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    """Generate reports and print their output paths."""
    args = parse_args()
    root = args.path.resolve()
    excludes = split_csv(args.exclude)
    thresholds = Thresholds(
        max_file_lines=args.max_file_lines,
        max_class_lines=args.max_class_lines,
        max_function_lines=args.max_function_lines,
        max_complexity_rank=args.max_complexity_rank,
        min_mi=args.min_mi,
    )
    reports = [build_file_report(path, root, thresholds) for path in iter_python_files(root, excludes)]
    reports.sort(key=lambda item: -report_score(item, thresholds))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "root": root.as_posix(),
        "thresholds": asdict(thresholds),
        "summary": summarize_reports(reports, thresholds),
        "file_reports": reports,
        "issue_candidates": build_issue_candidates(reports, thresholds),
        "xenon": run_xenon(root, excludes, args),
    }
    json_path, md_path = write_outputs(payload, args.output_dir.resolve())
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())