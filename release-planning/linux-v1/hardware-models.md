# Linux/NVIDIA hardware and model validation manifest (Linux v1)

Issue: https://github.com/Capsize-Games/airunner/issues/2086 (R02). Parent: https://github.com/Capsize-Games/airunner/issues/2083.

Documentation only. Every number below is either (a) cited from a real pinned value already committed in this checkout (file:line given), or (b) explicitly marked **PENDING** where no such source exists. Nothing here was measured by running the application, loading a model, or downloading anything — per this ticket's own instruction, this records upstream/in-repo evidence, not measured compatibility.

## 1. Proposed baseline platform

| Item | Value | Status | Source |
|---|---|---|---|
| OS | Ubuntu 24.04 LTS, x86_64 | Proposed (not yet validated) | Parent spec [#2083](https://github.com/Capsize-Games/airunner/issues/2083); matches the CI/build Docker base `nvidia/cuda:12.9.1-devel-ubuntu24.04` referenced at `shared/airunner_common/package_metadata.py:100` |
| GPU vendor | NVIDIA only for v1 | Proposed | Parent spec |
| Minimum VRAM | 16 GB | Proposed | Parent spec; consistent with the GPT-OSS 20B 4-bit estimate below (14 GB) leaving headroom, and inconsistent at 8-bit (20 GB — see §3) |
| CUDA toolkit / wheel line | 12.9 (`cu129`) | Pinned in this repo | `shared/airunner_common/package_metadata.py:105-113` (`ML_RUNTIME_REQUIREMENTS`: `torch==2.13.0+cu129`, `torchvision==0.28.0+cu129`, `torchaudio==2.11.0+cu129`), `:118` (`nvidia-cuda-runtime-cu12==12.9.79`) |
| Minimum NVIDIA driver version for CUDA 12.9 | **PENDING** | Not verified in this session | Would need NVIDIA's official CUDA Toolkit 12.9 release notes (a live lookup) — do not publish a specific driver version number without that citation |
| Minimum GPU compute capability | **PENDING** for the hard floor; 8.0 (Ampere) is the documented threshold for one optional fast path | Partially evidenced | `services/src/airunner_services/utils/memory/is_ampere_or_newer.py:9-12` gates flash-attention on `major >= 8` (Ampere+) — this is an optimization, not a hard requirement, so GPUs below Ampere are not thereby shown to be unsupported. The actual minimum compute capability the pinned `cu129` PyTorch wheel supports is not recorded anywhere in this repo and needs an upstream PyTorch release-notes citation before publishing a floor. |

## 2. Modalities and their models

Every modality actually shipped, per the verified feature matrix ([R01](https://github.com/Capsize-Games/airunner/issues/2084), `release-planning/linux-v1/feature-matrix.md`), with the model(s) behind it.

| Modality | Model(s) | Format | Source |
|---|---|---|---|
| Art — Stable Diffusion | SDXL Base 1.0 (`stabilityai/stable-diffusion-xl-base-1.0`, branch `main`); SDXL Turbo (`stabilityai/sdxl-turbo`, branch `main`); SDXL Inpaint (`diffusers/stable-diffusion-xl-1.0-inpainting-0.1`, branch **`fp16`**) | diffusers / safetensors | `services/src/airunner_services/bootstrap/model_bootstrap_data.py:6-51` |
| Art — Z-Image | Z-Image Turbo (`Tongyi-MAI/Z-Image-Turbo`, branch `main`) | diffusers / safetensors | same file, `:40-50` |
| LLM — chat | Qwen3.5 9B (`Qwen/Qwen3.5-9B`, branch `main`), default; GPT-OSS 20B (`openai/gpt-oss-20b`, branch `main`), optional | transformers, with a GGUF pre-quantized path preferred | `model_bootstrap_data.py:53-76`; GGUF repos `services/src/airunner_services/llm/provider_config.py:56` (`unsloth/Qwen3.5-9B-GGUF`), `:95` (`unsloth/gpt-oss-20b-GGUF`) |
| LLM — embeddings | Intfloat E5 Large (`intfloat/e5-large`, branch `main`) | transformers | `model_bootstrap_data.py:76-86` |
| STT | Whisper large-v3 via whisper.cpp sidecar | GGML (`ggml-large-v3.bin`), whisper.cpp pinned to commit `9386f23...` / tag `v1.8.4` | `native/runtime_sidecars/runtime_pins.env:7-9`; default STT path `shared/airunner_common/settings.py` (`AIRUNNER_DEFAULT_STT_HF_PATH`/`AIRUNNER_DEFAULT_STT_MODEL_FILENAME`, see that file's own drift-resolution note at the top) |
| TTS | eSpeak (CPU, no model download) and OpenVoice | eSpeak: none; OpenVoice: PyTorch checkpoint | Confirmed present via `services/src/airunner_services/runtimes/{espeak_model_manager,openvoice_model_manager}.py` (see feature matrix VOICE-03/04) |
| Local LLM inference backend | llama.cpp sidecar | native binary, pinned to commit `47a3966...` / tag `b10000` | `native/runtime_sidecars/runtime_pins.env:3-5` |
| RMBG (background removal) | present per feature matrix (ART-07) | — | `services/src/airunner_services/art/managers/rmbg/rmbg_model_manager.py` — **no pinned revision/digest found**; flagging as an open gap alongside D01's model-pinning work |
| Content-safety / policy models | **Undecided** | — | Explicitly not yet selected — see [S07](https://github.com/Capsize-Games/airunner/issues/2094) ("Select offline contextual and image safety evaluators with evidence"), which this manifest cannot anticipate. `services/src/airunner_services/model_management/model_registry.py:53` (`compute_capability_min`) exists as a schema field but is **never populated for any registered model** — another undecided/unused piece of the resource-arbitration path worth resolving alongside S07/S08/S09. |

## 3. VRAM/RAM estimates (from in-repo resource-arbitration data, not measured)

These are the engineering estimates the app's own model-resource-arbitration subsystem already carries (`model_management/model_registry.py`, `llm/provider_config.py`) — real, committed numbers, not something invented for this manifest. They have **not** been independently measured against real hardware in this session.

| Model | 4-bit VRAM | 8-bit VRAM | Fits 16 GB card? | Source |
|---|---|---|---|---|
| Qwen3.5-9B | 10 GB | 12 GB | Yes, either quantization | `llm/provider_config.py:53-54` |
| GPT-OSS 20B | 14 GB | 20 GB | **4-bit only** — 8-bit needs ~20 GB, over the 16 GB minimum | `llm/provider_config.py:92-93` |
| SDXL Base 1.0 | — | — (`min_vram_gb=6.0`, `recommended_vram_gb=8.0`) | Yes | `model_management/model_registry.py:227-239` |
| Z-Image Turbo | 4-bit: ~4 GB total; 8-bit: ~7-8 GB total; bf16: ~14 GB total | — | Yes at 4-bit/8-bit; bf16 is tight on 16 GB once other models are also loaded | `art/managers/zimage/mixins/zimage_memory_mixin.py:108-115` (VAE tiling is called out there as "critical" on ≤16 GB cards at 8-bit) |
| Whisper large-v3 | — | — (registry entry: `min_vram_gb=4.0`, `recommended_vram_gb=6.0`) | Yes | `model_management/model_registry.py:257-273` — **note**: this registry entry cites `openai/whisper-large-v3` (transformers) and a GGML download target, which does not match the actual shipped whisper.cpp sidecar path in §2; flagging as a discrepancy between this registry and the real STT pipeline, not resolving it here |
| Intfloat E5 Large (embeddings) | Not separately tracked | Not separately tracked | Yes (small model, ~1.3 GB by upstream HF listing) | No `provider_config.py`/`model_registry.py` entry found for this model |

**Important caveat found while compiling this table**: `model_management/model_registry.py` also registers a "Bark" TTS model (`:242-254`) that does **not** appear anywhere in `model_bootstrap_data.py`'s actual default catalog and is not one of the two TTS engines confirmed shipped in §2 (eSpeak, OpenVoice). Treat `model_registry.py`'s estimates as the resource-arbitration subsystem's generic reference data, not a definitive list of what installs by default — the feature matrix and `model_bootstrap_data.py` are the authoritative source for what actually ships.

Total disk footprint for a "download every default model" install is **PENDING** — it would need to be computed from live HuggingFace repo listings (a network call), which this documentation-only ticket does not make. A rough floor from the sizes above (Qwen3.5-9B ~10-18 GB depending on format, SDXL Base ~7 GB, Z-Image ~5-14 GB, Whisper large-v3 ~3 GB) suggests **at least 30-40 GB** free disk for a typical default-model install, before accounting for GGUF alternates, OpenVoice, or any optional models a user enables. Mark this as a proposed planning floor, not a verified figure.

## 4. Shared-GPU scheduling assumptions

- The daemon already implements cross-modality VRAM arbitration (`model_management/_base_model_resource_manager.py`, `_minimum_vram_for()` at `:158-164`; `canvas_memory_tracker.py`, `model_resource_manager.py`, `quantization_strategy.py` per the feature matrix's DL-05 row) and reports live external GPU usage via `nvidia-smi`/`rocm-smi` (`_base_model_resource_manager.py:174-186`).
- This is the same arbitration mechanism [Q07](https://github.com/Capsize-Games/airunner/issues/2146) ("Validate shared GPU lifecycle across all modalities") is meant to validate manually — this manifest does not claim that validation has happened.
- Flash-attention (an optional performance path, not a correctness requirement) is disabled below compute capability 8.0 (`is_ampere_or_newer.py`, §1) and can also be force-disabled via `AIRUNNER_DISABLE_FLASH_ATTENTION`.

## 5. Manual validation test matrix (pending — for Q01-Q08 to fill in)

This is a template, not a report: every cell is deliberately empty/pending. It exists so the Q0x manual-validation tickets have one shared table to fill in rather than each inventing their own.

### 5a. 16 GB VRAM card (minimum spec)

| Scenario | Expected outcome | Result | Notes |
|---|---|---|---|
| Install / first run | Completes, all default models selectable | PENDING | |
| SDXL Base txt2img | Generates without OOM | PENDING | |
| SDXL Inpaint | Generates without OOM | PENDING | |
| Z-Image Turbo, 4-bit | Generates without OOM | PENDING | |
| Z-Image Turbo, 8-bit | Generates without OOM (VAE tiling active) | PENDING | per §3 caveat |
| Qwen3.5-9B chat, 4-bit and 8-bit | Responds without OOM | PENDING | |
| GPT-OSS 20B chat, 4-bit | Responds without OOM | PENDING | |
| GPT-OSS 20B chat, 8-bit | Expected to fail or require unload of other models (needs ~20 GB) | PENDING | per §3 |
| STT (whisper.cpp) + TTS round trip | Completes without OOM while LLM is loaded | PENDING | cross-modality arbitration, see §4 |
| RAG / embeddings (E5 Large) alongside chat | Completes without OOM | PENDING | |
| Full art -> chat -> voice sequence in one session | No GPU memory leak across modality switches | PENDING | this is exactly what Q07 targets |

### 5b. Higher-VRAM card (24 GB+, exact card PENDING owner hardware selection)

| Scenario | Expected outcome | Result | Notes |
|---|---|---|---|
| GPT-OSS 20B chat, 8-bit | Responds without OOM (should now fit) | PENDING | |
| Z-Image Turbo, bf16 (full precision) | Generates without OOM | PENDING | |
| Concurrent art + chat + voice without unloading | Succeeds without manual model unload | PENDING | tests whether 16 GB's forced sequential unload/reload behavior relaxes with headroom |
| Same install/session tests as §5a | All pass at least as well as the 16 GB matrix | PENDING | |

## Validation

Every file:line citation above was read directly from this checkout. No model was downloaded, no GPU was queried, and no application code was run to produce this document, per this ticket's own instruction not to claim measured compatibility.
