# Third-Party Notices

This file lists the third-party code that AIRunner vendors or distributes,
together with its license text and upstream origin, as required to comply with
the applicable open-source licenses (GitHub issue #2059).

AIRunner itself is licensed under the GNU General Public License v3 (see
[`LICENSE`](LICENSE)). The projects listed below are distributed as-is under
their own licenses; AIRunner does not claim copyright over them.

For the Linux v1 release-wide inventory — pinned dependencies,
native sidecars, downloaded models, policy data, redistributed
assets, and unresolved provenance blockers — see
[`release-planning/linux-v1/licenses.md`](release-planning/linux-v1/licenses.md)
(release issue #2113).

## Policy

Every vendored package directory (an immediate subdirectory of a `vendor/`
tree that contains Python sources) must:

1. Ship a `LICENSE` file inside the vendored directory itself, and
2. Be listed in this document by its repository-relative path.

This policy is enforced in CI by
[`scripts/check_third_party_notices.py`](scripts/check_third_party_notices.py)
via the pytest wrapper
[`services/tests/test_third_party_notices.py`](services/tests/test_third_party_notices.py).

## PyInstaller 6.12.0 bootloader

- **Upstream project:** `pyinstaller/pyinstaller`
- **Upstream URL:** https://github.com/pyinstaller/pyinstaller/tree/v6.12.0
- **License:** GNU GPL version 2 or later with the PyInstaller Bootloader Exception.
- **Distributed component:** the Linux onedir application bundle includes the PyInstaller bootloader. The exact license and exception text is shipped at `legal/third-party/pyinstaller-6.12.0-COPYING.txt`.
- **Source pin:** tag `v6.12.0`, commit `31dbe9ff477716e4790aa317bc9da68766d20659`.
- **Wheel source:** `pyinstaller-6.12.0-py3-none-manylinux2014_x86_64.whl`, SHA-256 `a2abf5fde31a8b38b6df7939bcef8ac1d0c51e97e25317ce3555cd675259750f`.

---

## melo — MeloTTS

- **Upstream project:** `myshell-ai/MeloTTS`
- **Upstream URL:** https://github.com/myshell-ai/MeloTTS
- **License:** MIT
- **No longer vendored here:** this fork moved to its own repository,
  [`Capsize-Games/airunner-tts-vendor`](https://github.com/Capsize-Games/airunner-tts-vendor)
  (issue #2195), which `airunner-services` now depends on as an ordinary
  published package rather than embedded source. Its own
  [`README.md`](https://github.com/Capsize-Games/airunner-tts-vendor#readme)
  and `melo/README.md`/`melo/LICENSE` are the current source of truth; the
  license text below is kept here as a historical record of what this
  distribution has depended on.
- **Pin:** Vendored from the upstream `main` branch at the time the TTS
  runtime was integrated into AIRunner (issue #2051); the exact upstream
  commit was never recorded (see the new repository's own README).

### melo License (MIT)

```
MIT License

Copyright (c) 2024 MyShell.ai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## openvoice — OpenVoice

- **Upstream project:** `myshell-ai/OpenVoice`
- **Upstream URL:** https://github.com/myshell-ai/OpenVoice
- **License:** MIT
- **No longer vendored here:** this fork moved to its own repository,
  [`Capsize-Games/airunner-tts-vendor`](https://github.com/Capsize-Games/airunner-tts-vendor)
  (issue #2195), which `airunner-services` now depends on as an ordinary
  published package rather than embedded source. Its own
  [`README.md`](https://github.com/Capsize-Games/airunner-tts-vendor#readme)
  and `openvoice/README.md`/`openvoice/LICENSE` are the current source of
  truth; the license text below is kept here as a historical record of
  what this distribution has depended on.
- **Pin:** Vendored from the upstream `main` branch at the time the
  OpenVoice TTS runtime was integrated into AIRunner (issue #2051); the
  exact upstream commit was never recorded (see the new repository's own
  README).

### openvoice License (MIT)

```
MIT License

Copyright 2024 MyShell.ai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Additional attributed code

The following files carry license headers from the upstream projects they were
derived from, even though they are not vendored packages managed by the check
above. Their headers are retained to preserve upstream attribution:

- `services/src/airunner_services/art/pipelines/z_image/*` — Apache-2.0
  headers retained from the Apache-2.0 licensed code they were derived from.
- `melo/text/tone_sandhi.py` in
  [`Capsize-Games/airunner-tts-vendor`](https://github.com/Capsize-Games/airunner-tts-vendor)
  — retains an Apache-2.0 header from its upstream origin within the
  MIT-licensed MeloTTS project.
- `src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/stt/templates/whisper_license_ui.py`
  — embeds the Whisper license text for display in the GUI setup wizard.

The service Whisper GGML model identity is pinned in the service
[`ModelRegistry`](services/src/airunner_services/model_management/model_registry.py).
The generic STT repository setting in vendored `airunner-common` is retained
for other consumers and does not select the service whisper.cpp artifact. See
the [service model identity record](release-planning/services/input-reviews/whisper-cpp-model-identity.md).

This section is informational only; the CI check applies to vendored package
directories.

## libuv — uvloop Linux runtime

- **Upstream project:** `libuv/libuv`
- **Upstream URL:** https://github.com/libuv/libuv
- **Version and source pin:** libuv 1.52.1, commit
  `1cfa32ff59c076ffb6ed735bbc8c18361558661f`, vendored by uvloop 0.23.0.
- **License notice:** [`packaging/licenses/libuv-LICENSE`](packaging/licenses/libuv-LICENSE)
  is the original `vendor/libuv/LICENSE` file (SHA-256
  `16de0c32b265cb7d46a6d3bd614f259dd4d693a5e26b3407b04aae8d73041f0c`).
  Linux bundles stage this notice in `legal/` alongside the other notices.

## watchfiles 1.3.0 Rust build dependencies

The selected watchfiles Linux wheel contains a compiled Rust extension built
with 26 external Cargo crates, including build-time crates. The package's MIT
license and the original license texts found in those crate archives are
included under [`packaging/licenses/watchfiles-rust-crates/`](packaging/licenses/watchfiles-rust-crates/).
The accompanying `watchfiles-rust-crates.source.json` maps each notice to its
crate and version, source path, source archive checksum, license expression,
and copied-file checksum. The recorded notice files include the MIT, Apache,
ISC, Unicode, Unlicense, and CC0 texts present in the reviewed crate sources.

## pydantic-core 2.50.2 Cargo dependency notices

Original legal and attribution files from the 101 registry crates in the
selected source Cargo.lock are included under
[`packaging/licenses/pydantic-core-rust-crates/`](packaging/licenses/pydantic-core-rust-crates/).
The source index records exact archive checksums and copied-file hashes.
This is a notice superset: the exact subset compiled into the selected Linux
wheel has not been established by a build log. It does not assert that all
101 crates are linked into that wheel. Linux bundles include these notices
alongside the installed Python dependency notices.
