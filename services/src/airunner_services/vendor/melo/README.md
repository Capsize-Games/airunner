# Vendored MeloTTS code

This directory contains vendored code from the upstream
[MeloTTS](https://github.com/myshell-ai/MeloTTS) project
(originally released under an MIT license).

## Origin and pin

- **Upstream project:** `myshell-ai/MeloTTS`
- **Upstream URL:** https://github.com/myshell-ai/MeloTTS
- **Pin:** vendored from the `main` branch of the upstream repository at the
  time the TTS runtime was integrated into AIRunner (issue #2051). The exact
  vendored commit is not re-pinned automatically; treat this directory as a
  snapshot that must be reviewed and updated deliberately.

## Local modifications

The vendored files are intentionally kept close to upstream so that merging
upstream fixes stays feasible. AIRunner applies the following local changes:

- **Supply-chain hardening:** `torch.load` calls load checkpoints with
  `weights_only=True` and refuse non-`.safetensors` checkpoints with a
  warning (issue #2036).
- **Logging hygiene:** interactive debugger breakpoints and bare `except:`
  blocks were replaced with logged warnings and graceful fallbacks
  (issue #2051).
- **Path resolution:** model and cache paths resolve through
  `airunner_services.vendor.melo.runtime_support` so the vendored code stays
  relocatable across machines and containers.
- **No application dependency (issue #2190):** this directory previously
  imported `airunner`/`airunner_common`/`airunner_services` directly (an
  enum, `AIRUNNER_BASE_PATH`, a `PathSettings` database lookup, the shared
  logger, and the shared GPU-memory-clearing helper). It now depends on
  nothing outside itself and the third-party packages it uses:
  - `language.py` defines a same-valued local `Language` enum instead of
    importing the application's `AvailableLanguage`.
  - `runtime_support.py` exposes `set_tts_model_root_resolver`,
    `set_tts_model_base_resolver` and `set_cache_base_resolver`, which
    `airunner_services.runtimes.openvoice_model_manager` registers at
    import time with the previous `PathSettings`-based lookups. Logging
    is a plain `logging.getLogger(...)`.
  - `api.py`'s `TTS.unload()` calls an injectable
    `set_memory_cleanup_hook` callable (the host registers the
    application's multi-GPU-aware `clear_memory`); its own default is a
    plain `gc.collect()` plus `torch.cuda.empty_cache()`.

## Licensing

The upstream MeloTTS project is MIT licensed (`Copyright (c) 2024 MyShell.ai`).
The AIRunner project does not own the copyright to the upstream files in this
directory.

- The MIT license text and the upstream copyright notice live in
  [`LICENSE`](LICENSE) in this directory (issue #2059).
- This package is also listed, with its full license text and upstream origin,
  in the top-level
  [`THIRD_PARTY_NOTICES.md`](../../../../../THIRD_PARTY_NOTICES.md)
  (issue #2059).
