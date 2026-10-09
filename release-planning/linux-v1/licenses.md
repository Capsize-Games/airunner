# Dependency and model license inventory (Linux v1)

Issue: https://github.com/Capsize-Games/airunner/issues/2113 (P11).
Parent: https://github.com/Capsize-Games/airunner/issues/2083.
Prerequisites: R02
(https://github.com/Capsize-Games/airunner/issues/2086, closed),
P05 (https://github.com/Capsize-Games/airunner/issues/2107,
closed), W01
(https://github.com/Capsize-Games/airunnerweb/issues/216, OPEN).
Status: evidence record, not a legal clearance. Written 2026-10-09
from this checkout plus read-only public metadata lookups dated
below. A coding agent cannot approve licensing; every BLOCKER row
needs an owner/counsel decision before release.

## 1. Scope and method

This inventory covers the Linux v1 services bundle
(`packaging/linux/services-bundle-spec.toml`), the desktop aggregate
it freezes (`services[desktop]` plus `airunner[nvidia]`, locked in
`package/constraints-linux-nvidia-cu129.txt`), vendored and
attributed code, native sidecar binaries, downloaded models,
detector/policy data, and redistributed assets. Each row records
version/revision, license, attribution or source obligations, and
whether the artifact is bundled or downloaded post-install.

This inventory makes no blanket permission claim: it does not state
that commercial use of any listed artifact is permitted, nor that
private policy data is automatically permitted for any use.
"PENDING" means no citable source was found in this session;
"BLOCKER" means the item must be resolved before release.

Upstream metadata cited below was read on 2026-10-09 via the
GitHub repository license API, the Hugging Face model API
(`cardData.license`), and PyPI JSON metadata. Live SHAs are
observations of upstream HEAD on that date, not pins the
application enforces.

## 2. Application license and Desktop GPL ancestry

AIRunner is GNU General Public License v3.0 only
(`GPL-3.0-only`): `LICENSE` is byte-identical to the canonical
GPL-3.0 text, the copyright statement lives in `NOTICE`
(Capsize LLC, 2026), and `RELICENSING.md` records the history:
MIT (Capsize Games, 2023-2024), then GPL-3.0-only (Capsize LLC,
2026 onward). MIT is GPL-compatible, so the relicense required no
contributor permission; MIT grants on pre-2026 code stand for
that code. Every `license=` metadata field agrees
(`services/setup.py`, root `setup.py`, per issue #2058), and
`debian/copyright` carries the machine-readable declaration.

GPL distribution of a paid installer requires a written
corresponding-source offer. The offer text is PENDING owner and
counsel approval (BLOCKER B-8); the staged legal files (§9) are
the vehicle, not the offer itself.

## 3. Dependency inventory

Authoritative pin set (release issue P02):

- Constraint lock: package/constraints-linux-nvidia-cu129.txt
- Constraint lock sha256:
  76e7ddd0af39de0b2131ba3f723299b51c8126dacc172c17af32d097ca844594
- Constraint pins: 352
- Profile roots: `./[nvidia]`, `./services[desktop]`,
  `./native` (installed from the local tree, not pinned in the
  lock). Verified consumption and regeneration are documented in
  the lock file header.

`services/tests/test_release_p11.py` recomputes the sha256 and
pin count, so any regeneration without updating this section
fails the suite.

### 3.1 Selected direct dependencies (verified 2026-10-09)

Bundled means frozen into the PyInstaller directory bundle;
downloaded means fetched at install or first use.

| Distribution (pinned version) | License | Source | Bundled? |
|---|---|---|---|
| torch 2.13.0+cu129, torchvision 0.28.0+cu129, torchaudio 2.11.0+cu129 | BSD-3-Clause | Upstream `pytorch/pytorch` LICENSE text (BSD redistribution clauses verified) | Bundled |
| nvidia-cuda-runtime-cu12 12.9.79 | NVIDIA proprietary (CUDA EULA) | PyPI `LicenseRef-NVIDIA-Proprietary` | Bundled |
| PySide6 / PySide6-Addons / PySide6-Essentials / shiboken6 6.9.0 (GUI dist only, never in the services bundle) | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | PyPI license field | GUI bundle only |
| transformers 5.8.1, diffusers 0.38.0, optimum 1.25.1, tokenizers 0.22.2, safetensors 0.8.0, accelerate 1.14.0, huggingface-hub, sentence-transformers 5.6.1 | Apache-2.0 | PyPI metadata / upstream license endpoints | Bundled |
| llama-cpp-python 0.3.21 | MIT | PyPI metadata | Bundled |
| bitsandbytes 0.46.1 | MIT | Upstream `TimDettmers/bitsandbytes` license endpoint | Bundled |
| pyttsx3 2.91 | MPL-2.0 (upstream `nateshmbhat/pyttsx3`); GPL-3.0 compatibility of the combined work needs the Exhibit B / secondary-license check (BLOCKER B-6) | Upstream license endpoint; no PyPI metadata | Bundled |
| airunner-common ~= 6.1.7 (Capsize) | GPL-3.0-only | Upstream `Capsize-Games/airunner-common` license endpoint; `.deb` embeds wheel 6.1.7 verbatim, sha256 `a7d975b7...c970` (`debian/vendor/README.source`) | Bundled |
| airunner-tts-vendor ~= 0.1 (Capsize) | MIT declared in its `pyproject.toml`; `melo/` and `openvoice/` carry their own upstream MIT LICENSE files; no top-level LICENSE by design (its README). Exact upstream commit never recorded (BLOCKER B-5) | Upstream repo (GitHub license endpoint: no file detected), `THIRD_PARTY_NOTICES.md` | Bundled |
| facehuggershield == 1.0.0 (Capsize) | GPL-3.0 | PyPI metadata (author Capsize LLC) | Bundled |

### 3.2 Long tail

The remaining pins in the 352-entry lock are inventoried by
name, exact version, and per-file hashes in the lock itself.
Per-package license confirmation for the full set is PENDING a
machine-readable license scan of the frozen bundle in release
CI (BLOCKER B-7). No row here may be read as clearing the
unscanned tail.

## 4. Vendored and attributed code

- `find services/src src -type d -name vendor` returns nothing:
  no vendored package directories remain, so
  `scripts/check_third_party_notices.py` passes vacuously (also
  asserted by `test_third_party_notices.py` and §11).
- `services/src/airunner_services/art/pipelines/z_image/*.py`
  (4 files): adapted from the diffusers library `main` branch
  for AIRunner; Apache-2.0 headers retained
  (Copyright 2025 Alibaba Z-Image Team and The HuggingFace
  Team). The header states the copy should be removed once
  ZImagePipeline ships in a stable diffusers release.
- `melo/` and `openvoice/`: no longer vendored here; see the
  airunner-tts-vendor row in §3.1.
- `src/airunner/.../stt/templates/whisper_license_ui.py`:
  embeds license text for display in the GUI setup wizard
  (first-party UI file, informational only).

## 5. Native binaries

- Sidecar pin (.github/native-sidecar-version): v0.1.0
- Source: `Capsize-Games/airunner-native` release bundle
  `runtime-sidecars-linux.tar.gz` (consumed by
  `scripts/install.sh` and the release workflow per P03).
- Binaries: `llama-server` (CHAT-03), `whisper-server`
  (VOICE-02), staged into the bundle `bin/` dir post-freeze by
  `packaging/linux/stage-sidecars.sh`.
- airunner-native is GPL-3.0 (upstream license endpoint).
  Upstream `ggerganov/llama.cpp` and `ggerganov/whisper.cpp`
  are each MIT (upstream license endpoints). The exact
  upstream llama.cpp/whisper.cpp commits inside the v0.1.0
  bundle are PENDING confirmation from that repo's own
  manifest (BLOCKER B-4).

## 6. Models (downloaded post-install, never bundled)

The bundle spec `[exclusions]` rejects weight files (`*.gguf`,
`*.safetensors`, `*.pt`, `*.pth`, `*.ckpt`, `*.onnx`) anywhere
in the bundle. Models resolve through
`HuggingFaceDownloadWorker._resolve_bootstrap_revision`, which
reads the `branch` declared in
`services/src/airunner_services/bootstrap/model_bootstrap_data.py`.
Those pins are branch names (all `main`), not immutable
commit SHAs: upstream can move under them (BLOCKER B-3). The
SHAs below are live HEAD observations from 2026-10-09.

| Model (repo path) | Revision pin | License (Hub card, 2026-10-09) | Notes |
|---|---|---|---|
| Tongyi-MAI/Z-Image-Turbo | branch `main` | apache-2.0 | Sole art model (not flagged default) |
| Qwen/Qwen3.5-9B (default chat) and unsloth/Qwen3.5-9B-GGUF (preferred quantized path) | branch `main` | apache-2.0 (both cards) | `provider_config.py` prefers the GGUF path |
| openai/gpt-oss-20b (optional chat) and unsloth/gpt-oss-20b-GGUF | branch `main` | apache-2.0 (both cards) | Optional |
| intfloat/e5-large (embeddings) | branch `main` | mit | Local embeddings |
| openai/whisper-large-v3 via whisper.cpp sidecar (`ggml-large-v3.bin`) | sidecar pin v0.1.0 + branch `main` | apache-2.0 (Hub card for the transformers repo; GGML file provenance is the whisper.cpp model download) | Default STT path |
| OpenVoice checkpoints (TTS) | PENDING: no pinned revision found in this checkout | PENDING: checkpoint license not verified (BLOCKER B-2) | eSpeak (CPU, no model file) is the other TTS engine |
| RMBG (background removal, ART-07) | PENDING: no pinned revision or digest found (already flagged in R02) | PENDING (BLOCKER B-2) | Ships per the feature matrix but has no recorded pin |
| Content-safety / policy models | Undecided (S07, see §7) | Undecided (BLOCKER B-9) | Cannot be inventoried before selection |

Live HEAD SHAs observed 2026-10-09 (informational only):
Z-Image Turbo `f332072aa78b`,
Qwen3.5-9B `c20223623576`, gpt-oss-20b `6cee5e81ee83`,
e5-large `4dc6d853a804`, whisper-large-v3 `06f233fe06e7`,
Qwen3.5 GGUF `3885219b6810`, gpt-oss GGUF `d449b42d93e1`.

## 7. Detector and policy data

- `services/src/airunner_services/content_safety/data/policy_terms.dat`
  in this checkout is a versioned-artifact placeholder; the
  signature (`.dat.sig`) is `required=false` in the bundle
  spec because signed production policy is provisioned only in
  trusted release CI (S06). Production policy bytes must never
  appear in source, tests, or logs.
- Offline contextual and image-safety evaluator selection
  (S07, https://github.com/Capsize-Games/airunner/issues/2094)
  is undecided, so no detector model or private policy
  vocabulary can be inventoried here (BLOCKER B-9). Nothing in
  this document permits private policy data for any use.

## 8. Redistributed assets

- `services/src/airunner_services/assets/reference_speakers/bobross.wav`
  (1.9 MB, shipped via `package_data` and the bundle spec):
  no accompanying source, speaker-consent, or rights record
  was found in this checkout (BLOCKER B-10).
- Alembic migrations, `alembic.ini`, and `bin/*.sh` staged by
  the bundle spec are first-party GPL-3.0 sources, not
  third-party redistributions.

## 9. Notices and source-offer material

Present in this checkout and staged to the bundle `legal/`
directory by `services-bundle-spec.toml` (`stage = "root"`,
`required = true`): `LICENSE`, `NOTICE`,
`THIRD_PARTY_NOTICES.md`. `debian/copyright` is the
machine-readable declaration for the `.deb`. The written
corresponding-source offer itself is PENDING (BLOCKER B-8).

## 10. Unresolved provenance and release blockers

- BLOCKER B-1: RESOLVED by
  https://github.com/Capsize-Games/airunner/issues/2249
  (SDXL support stripped 2026-10-09): the
  `stabilityai/stable-diffusion-xl-base-1.0` (`openrail++`),
  `stabilityai/sdxl-turbo` (`sai-nc-community`,
  non-commercial), and SDXL Inpaint (`openrail++`) rows
  left §6 with the bootstrap catalog, so no Stability
  weights remain to ship or auto-download and no
  Stability-terms counsel decision is needed. No
  commercial-use permission is claimed here.
- BLOCKER B-2: Unpinned model artifacts. OpenVoice
  checkpoints and the RMBG model have no recorded
  revision/digest or verified license in this checkout.
- BLOCKER B-3: Branch pins, not immutable digests. All
  bootstrap models resolve a branch (`main`); D01 did
  not produce immutable commit SHAs. Upstream movement can
  change what users download.
- BLOCKER B-4: Sidecar upstream commits. The llama.cpp and
  whisper.cpp revisions inside airunner-native v0.1.0 are not
  recorded in this checkout; confirm from that repo's manifest.
- BLOCKER B-5: TTS fork provenance gap. airunner-tts-vendor
  records no exact upstream myshell-ai commit (acknowledged in
  its README); counsel decides whether the MIT subtree
  notices suffice.
- BLOCKER B-6: pyttsx3 MPL-2.0 secondary-license check.
  Confirm the combined GPL-3.0 work satisfies MPL-2.0 §3.3
  (no "Incompatible With Secondary Licenses" exhibit).
- BLOCKER B-7: Full-tree license scan. The 352-pin lock
  beyond §3.1 needs a machine-readable scan of the frozen
  bundle in release CI before any clearance statement.
- BLOCKER B-8: Written corresponding-source offer text needs
  owner/counsel approval before GPL distribution.
- BLOCKER B-9: Safety evaluator selection (S07) is undecided;
  detector models and private policy data cannot be cleared
  before they exist.
- BLOCKER B-10: `bobross.wav` reference-speaker rights record
  is missing (source, consent, voice terms).
- BLOCKER B-11: Web MIT ancestry. The companion port
  (`services/src/airunner_services/llm/companion/`, mapped in
  B01 `release-planning/linux-v1/companion-contracts.md`)
  derives from MIT-licensed airunnerweb
  (https://github.com/Capsize-Games/airunnerweb, SPDX MIT),
  but the W01 freeze
  (https://github.com/Capsize-Games/airunnerweb/issues/216,
  PR https://github.com/Capsize-Games/airunnerweb/pull/221)
  is still OPEN, so ported-behavior provenance is not yet
  frozen or reviewed. MIT is GPL-compatible, but the freeze
  and per-capability mapping review must land first.

## 11. Acceptance checklist

- [ ] Every selected bundle/model artifact has a
  license/provenance row: §3-§8 tabulate the bundle spec
  payloads, the 352-pin lock, both sidecars, and every
  bootstrap model; gaps stay as explicit PENDING/BLOCKER
  rows, never silent omissions.
- [ ] Required notices/source-offer material is present;
  unresolved rights remain explicit release blockers: §9
  lists staged notices; §10 keeps B-2..B-11 open (B-1
  resolved by #2249).
- [ ] No claim that commercial use or private policy data is
  automatically permitted: §1 states the guardrail; ex-B-1
  records the removed non-commercial default model; §7
  withholds private policy data.

## 12. Reviewer and operator fields

- Operator name: PENDING
- Operator date (UTC): PENDING
- Reviewer name: PENDING
- Reviewer date (UTC): PENDING
- Candidate: PENDING (bundle-manifest identity per the C01
  gate record)
- License scan tool and version: PENDING (needed to close
  BLOCKER B-7)
- Counsel decision refs (B-5, B-6, B-8, B-10, B-11):
  PENDING
- Reviewer acceptance: PENDING (the issue stays open until
  this exists)

## 13. Source references

In-checkout: `LICENSE`, `NOTICE`, `RELICENSING.md`,
`THIRD_PARTY_NOTICES.md`, `debian/copyright`,
`debian/vendor/README.source`,
`packaging/linux/services-bundle-spec.toml`,
`packaging/linux/stage-sidecars.sh`,
`package/constraints-linux-nvidia-cu129.txt`,
`services/setup.py`, root `setup.py`,
`services/src/airunner_services/bootstrap/model_bootstrap_data.py`,
`services/src/airunner_services/downloads/huggingface_download_worker.py`,
`services/src/airunner_services/llm/provider_config.py`,
`services/src/airunner_services/art/pipelines/z_image/`,
`.github/native-sidecar-version`,
`release-planning/linux-v1/hardware-models.md`,
`release-planning/linux-v1/feature-matrix.md`,
`release-planning/linux-v1/companion-contracts.md`.
Upstream (read 2026-10-09): GitHub license endpoints for
`ggerganov/llama.cpp` (MIT), `ggerganov/whisper.cpp` (MIT),
`Capsize-Games/airunner-native` (GPL-3.0),
`Capsize-Games/airunner-common` (GPL-3.0),
`Capsize-Games/airunnerweb` (MIT), `pytorch/pytorch` LICENSE
(BSD-3-Clause text), `UKPLab/sentence-transformers`
(Apache-2.0), `TimDettmers/bitsandbytes` (MIT),
`nateshmbhat/pyttsx3` (MPL-2.0); Hugging Face model API
license tags for the seven §6 repos; PyPI JSON metadata for the
§3.1 distributions.
