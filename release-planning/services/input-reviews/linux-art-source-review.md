# Linux art-generation dependency source review

Review date: 2026-11-02

This records static review of the exact locked inputs `DeepCache==0.1.1`,
`gguf==0.17.1`, and `tomesd==0.1.3`. Source-input review is separate from
installed-artifact validation and model/runtime acceptance. No package was
installed or imported, and no model was loaded or downloaded. Do not read this
as evidence that a generated image or production pipeline was exercised.

## Artifacts and source identities

Each PyPI wheel and sdist was downloaded from its release JSON and checked
against the published filename, size, and SHA-256. Python sources common to
the wheel and sdist were byte-identical for all three packages. This verifies
the reviewed wheel/source contents against each other; it is not a reproducible
build claim. PyPI's release `vulnerabilities` field was empty for each exact
version when checked on the review date.

| Distribution | Wheel SHA-256 (bytes) | Sdist SHA-256 (bytes) | Source revision and private copy |
| --- | --- | --- | --- |
| `DeepCache==0.1.1` | `aa4aa5f8e9a2e5a41d59900305c3c86c20834537d0c67bf2d8bb7075618ae48a` (190872) | `8bc995d8c0ee7f3eb51ca080c951916bf0eb044ebdc75215b1753621ac8f80e6` (190065) | `horseee/DeepCache`, commit `a89b2d404c4d7311c5905f193056429371da17bb` (2023-12-30); all 25 Python files at matching paths agree, with only `setup.py` differing in the version field. Mirrored to private `Capsize-Games/deepcache-maintenance`; Actions disabled. |
| `gguf==0.17.1` | `7bc5aa7eeb1931f7d39b48fdc5b38fda6b294b9dca75cf607ac69557840a3943` (96224) | `36ad71aad900a3e75fc94ebe96ea6029f03a4e44be7627ef7ad3d03e8c7bcb53` (89338) | `ggml-org/llama.cpp`, tag `gguf-v0.17.1`, peeled commit `381174bbdaf10d6a80dc2099f284b20544d86962`, `gguf-py/`; all 17 matching Python files agree. Tag retained in private `Capsize-Games/llama-cpp-maintenance`; Actions disabled. |
| `tomesd==0.1.3` | `3d5aa0857fe2c2aab253891050601ca13a87d8d7a99b6760b9ca0856aa0c6355` (11467) | `15bba2e952f4643c8355951e892fda918ddccbdff2238dc368d42bd078fcedc9` (14032) | `dbolya/tomesd`, tag `v0.1.3`, commit `dc08c1bb06b670ff2c67082ad684ae5301e0ec4b3`; all five matching Python files agree. Mirrored to private `Capsize-Games/tomesd-maintenance`; Actions disabled. |

The private DeepCache copy contains the full upstream branch history, including
the commit above, but has no upstream release tag for 0.1.1. The sdist's
`setup.py` sets `v0.1.1`, whereas the matching source commit's setup file sets
`v0.1.0`; the Python implementation agrees. This provenance/packaging delta is
recorded rather than treated as an exact whole-tree match.

The artifacts are retained under the ignored path
`.headlesscode/service-audit-2026-11-02/art-generation-source-review/artifacts/`
for later notice and digest integration. No downloaded model data is present.

## Static findings

### DeepCache

The wheel uses the legacy setuptools `setup.py` build path. Its declared runtime
dependencies are unbounded `torch`, `diffusers`, and `transformers`; the
candidate lock supplies versions separately. The reviewed wheel contains
Python implementation and the complete Apache-2.0 `LICENSE` (SHA-256
`0573beb04a83347a7b344d7771d26c40532d54c7ba732c41bb17e403a0962453`). No
custom install hook, subprocess execution, or automatic external request was
found in the package's install path. The copied Diffusers-style
`from_pretrained` helpers can access remote model repositories and accept the
normal model authentication inputs when explicitly called; those calls are
not initiated just by importing the helper or installing its wheel.

The service imports `DeepCacheSDHelper` in its Stable Diffusion model-loading
path and has explicit helper enable/disable calls. Static inspection did not
execute that path. The source also contains `DeepCache/flops.py`, which states
that it is adapted from Sovrasov's and Lyken17's projects under MIT terms, but
the release archive carries only the Apache license file. Preserve the
upstream MIT notices in the final bundle; do not treat the Apache file as
covering that third-party code. The source header identifies the package path
and repositories but does not record exact upstream commits. The private
DeepCache history shows `DeepCache/flops.py` was first added at commit
`0540d34148b17b1a484333930eb43128016cec9a` on 2023-12-20. Therefore, the
license source commits below are pinned review snapshots available by that
attribution date, not a claim that the package header specifies its exact
upstream code commits.

The byte-preserved MIT license files are now in
`packaging/licenses/DeepCache-0.1.1-supplement/`. `LICENSE-ptflops.txt` is from
`sovrasov/flops-counter.pytorch` commit
`8781ecff9f56b64e3618314cb0df15d6a76f3bc6`, `LICENSE` (1075 bytes, SHA-256
`c791d032af35123823c6e163ae0c453c72304fa225483961d869979001237e64`), with
the original `Vladislav Sovrasov` copyright line. `LICENSE-thop.txt` is from
`Lyken17/pytorch-OpCounter` commit
`43c064afb71383501e41eaef9e8c8407265cf77f`, `LICENSE` (1067 bytes, SHA-256
`36f577ad288f1beae8188b6ec09808eaed278c08b8284bacc694bb56ffbf3dfc`), with
the original `Ligeng Zhu` copyright line. Both commits and full histories are
preserved in their private Actions-disabled maintenance repositories. The
second repository changed its current license after the pinned historical
MIT revision; the supplement reproduces the historical MIT text and does not
represent its current upstream license.

`source-manifest.json` binds both notice hashes to those exact upstream
repository/revision/path records and separately binds the package evidence to
`DeepCache-0.1.1/DeepCache/flops.py` in the pinned sdist
(SHA-256 `788c6a9dff7bb8905bec418f5853ca56d815304c6f5dc0bafe7c9327837ac430`),
whose overall SHA-256 is recorded in the artifact table. The notice texts are
not represented as files from that sdist. The notice loader now emits
`reviewed-upstream-source-supplement` records for this provenance form; final
bundle collector integration remains a separate step. No original copyright
line or license text was rewritten.

### GGUF

The wheel is pure Python; its build metadata uses `poetry-core>=1.0.0`, but the
candidate consumes the verified wheel, so no sdist build backend is run. The
wheel carries an MIT `LICENSE` (SHA-256
`ef78c7e6659e34c798194f0d344e807c722de70cbca1359ef54772661e11ca38`). Its
default runtime dependencies are `numpy`, `pyyaml`, and `tqdm`; PySide6 is only
the optional `gui` extra.

AIRunner uses `GGUFReader` for local GGUF metadata and imports quantization
definitions for its GGUF operations. No AIRunner call to `SafetensorRemote` or
other remote-helper method was found. The package does include an opt-in
`SafetensorRemote` helper that issues HTTP(S) GET/HEAD requests, follows
redirects, and can add `HF_TOKEN` as a bearer header. It accepts a URL from its
caller without an application-level host allowlist. This behavior is explicit
method invocation, not import-time telemetry or automatic background access;
keep future use limited to a separately validated, trusted Hugging Face URL
flow and do not pass untrusted arbitrary URLs to it.

### TomeSD

The wheel uses a simple setuptools build and declares `torch>=1.12.1`. The
wheel includes the full MIT license (SHA-256
`1f97152807aa1d5d0420b8a07c7b0ce058d0a76ffd808f865a5144e747a2f96f`). Static
inspection found no package network or credential access and no custom install
hook. `apply_patch` intentionally replaces model-block classes/forward methods
and adds a forward pre-hook; `remove_patch` is provided to undo it. The
implementation uses randomized token merging, so output changes are an
expected consequence of enabling the feature. AIRunner gates this call on its
ToMe setting/environment option and removes the patch when disabled. The
service path and GPU behavior were not run.

## Review disposition and exclusions

The three pinned source inputs have bounded static source/package review for
installation into isolated candidate builds. This disposition does not grant
artifact acceptance or runtime/model acceptance. No advisory appeared in
PyPI's exact-release vulnerability fields; this is not a claim that the
versions have no undisclosed or unindexed issues. The DeepCache MIT notices
are now preserved as source-backed supplement inputs, pending final collector
integration. GGUF's optional
remote helper should not be exposed to unvalidated URLs. No runtime, model
download, real image generation, GPU, offline-denial, or installed-package
smoke test was performed here.
