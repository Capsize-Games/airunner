# Service acceptance fixtures, version 1

These fixtures define inputs and scoring before physical model runs. They are
unrun. Keep the prompt IDs, tool schemas, answers, positions, and scoring rules
immutable after observing outputs; corrections require a new fixture version.

## ART

`art_zimage_turbo_4bit_v1.json` has 20 neutral fixed prompts for the exact
reviewed `Tongyi-MAI/Z-Image-Turbo` revision
`f332072aa78be7aecdf3ee76d5c247082da564a6`. Each request is one 512×512 image,
eight steps, a fixed seed, CFG 0, and `FLOW_MATCH_EULER`; select `dtype=4bit`
in isolated `GeneratorSettings`. The source loader supports 4-bit NF4 for
pretrained directories. Reject an unsupported mode rather than substituting a
different one. Automated file checks are separate from the four-criterion
assistant visual rubric. The fixture does not claim a human review or safety
evaluation.

## Qwen tool selection and long context

`qwen35_tool_selection_v1.json` freezes 20 expected tool/no-tool decisions
against supplied read-only mock tools. The OpenAI-compatible endpoint supports
caller-supplied tools; generated `tool_calls` are returned unexecuted for the
caller. Score tool choice and JSON arguments only. Do not execute fixture tools
against external services or user data. Record the complete request, prompt,
model/template, tool schemas, thinking choice, seed/sampling settings,
provider usage, response, and failures.

`qwen35_long_context_v1.json` freezes 20 synthetic retrieval questions and
answers placed at beginning, middle, or end positions. Its companion
`build_qwen35_long_context.py` uses the local tokenizer directory supplied at
run time to build prompts near 30,000 user-content tokens. It makes no fixed
token-count claim before generation. The generated request must keep the
Qwen3.5-9B Q8_0 runtime profile at `n_ctx=32768`, record tokenizer and
provider-reported input/output counts, and leave enough context for the
configured output plus chat-template overhead. No smaller model, quantization,
or context is a substitute for the target scenario.

All fixtures remain unrun. Resource rejection is recorded as capacity
unavailable, never as a model result. No model activation or dependency change
is part of fixture preparation.
