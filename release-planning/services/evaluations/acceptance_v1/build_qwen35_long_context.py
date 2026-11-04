#!/usr/bin/env python3
"""Build tokenizer-counted Qwen3.5 synthetic long-context inputs.

This imports only the local tokenizer. It never loads model weights or sends
requests. Generated JSONL contains complete inputs and must be retained with
the service run receipt.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "qwen35_long_context_v1.json"
TOKENS = {
    "beginning": 900,
    "middle": 15000,
    "end": 28500,
}
FILLER = (
    "The daily operations record notes routine maintenance, a clear work area, "
    "and the use of labeled containers. Staff check the paper copy after each "
    "shift and return it to the archive shelf. "
)
SYSTEM = (
    "Answer using the one matching synthetic evidence sentence in the user "
    "message. Ignore unrelated routine notes. Return only the requested value. "
    "Do not guess if the evidence is absent."
)


def count(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def repeat_near(tokenizer, prefix: str, repeated: str, suffix: str, target: int) -> str:
    """Choose a repeated filler count whose complete rendered text nears target."""
    low, high = 0, max(2, target // max(1, count(tokenizer, repeated)) + 4)
    while low < high:
        middle = (low + high + 1) // 2
        size = count(tokenizer, prefix + repeated * middle + suffix)
        if size <= target:
            low = middle
        else:
            high = middle - 1
    candidates = {max(0, low - 1), low, low + 1}
    best = min(
        candidates,
        key=lambda n: abs(count(tokenizer, prefix + repeated * n + suffix) - target),
    )
    return repeated * best


def build_case(tokenizer, case: dict, target: int) -> dict:
    prefix = (
        "SYNTHETIC ARCHIVE TRANSCRIPT. The following records are fictional. "
        "Routine notes may repeat and are not evidence for the final question.\n\n"
    )
    anchor_target = TOKENS[case["position"]]
    left = repeat_near(tokenizer, prefix, FILLER, case["needle"], anchor_target)
    before_evidence = prefix + left
    right_prefix = before_evidence + "\nEVIDENCE: " + case["needle"] + "\n\n"
    ending = (
        "END OF ARCHIVE. Use the evidence sentence that exactly names the item "
        "asked about.\n\nQUESTION: " + case["question"]
    )
    right = repeat_near(tokenizer, right_prefix, FILLER, ending, target)
    prompt = right_prefix + right + ending
    total = count(tokenizer, prompt)
    anchor_index = count(tokenizer, before_evidence + "\nEVIDENCE: ")
    if total < target - 250:
        raise RuntimeError(f"{case['id']} prompt too short after tokenization: {total} < {target - 250}")
    if abs(anchor_index - anchor_target) > 250:
        raise RuntimeError(
            f"{case['id']} evidence position {anchor_index} outside tolerance "
            f"for target {anchor_target}"
        )
    return {
        "fixture_id": "airunner-qwen35-long-context-v1",
        "case_id": case["id"],
        "system_prompt": SYSTEM,
        "user_prompt": prompt,
        "question": case["question"],
        "expected_answer": case["expected_answer"],
        "evidence_sentence": case["needle"],
        "position_band": case["position"],
        "target_evidence_token_index": anchor_target,
        "actual_evidence_token_index": anchor_index,
        "actual_user_content_tokens": total,
        "target_user_content_tokens": target,
        "max_output_tokens": 128,
        "configured_context_tokens": 32768,
        "raw_content_plus_output_headroom_tokens": 32768 - total - 128,
        "note": "Tokenizer count covers rendered user text only. Record service/provider prompt token usage and actual chat-template overhead during a run; this file is not a generation result.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-user-tokens", type=int, default=30000)
    args = parser.parse_args()
    if not args.tokenizer_dir.is_dir():
        parser.error("--tokenizer-dir must be an existing local directory")
    if not 29_000 <= args.target_user_tokens <= 30_500:
        parser.error("target must be 29,000 to 30,500 user-content tokens to reserve chat-template and output headroom")

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        args.tokenizer_dir,
        local_files_only=True,
        trust_remote_code=False,
        use_fast=True,
    )
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = [build_case(tokenizer, case, args.target_user_tokens) for case in fixture["cases"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "case_count": len(rows),
        "tokenizer_class": type(tokenizer).__name__,
        "tokenizer_directory": str(args.tokenizer_dir.resolve()),
        "user_content_tokens_min": min(row["actual_user_content_tokens"] for row in rows),
        "user_content_tokens_max": max(row["actual_user_content_tokens"] for row in rows),
        "physical_run": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
