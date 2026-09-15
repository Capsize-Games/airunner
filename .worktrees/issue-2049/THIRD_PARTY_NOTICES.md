# Third-Party Notices

This file lists the third-party code that AIRunner vendors or distributes,
together with its license text and upstream origin, as required to comply with
the applicable open-source licenses (GitHub issue #2059).

AIRunner itself is licensed under the GNU General Public License v3 (see
[`LICENSE`](LICENSE)). The projects listed below are distributed as-is under
their own licenses; AIRunner does not claim copyright over them.

## Policy

Every vendored package directory (an immediate subdirectory of a `vendor/`
tree that contains Python sources) must:

1. Ship a `LICENSE` file inside the vendored directory itself, and
2. Be listed in this document by its repository-relative path.

This policy is enforced in CI by
[`scripts/check_third_party_notices.py`](scripts/check_third_party_notices.py)
via the pytest wrapper
[`services/tests/test_third_party_notices.py`](services/tests/test_third_party_notices.py).

---

## melo — MeloTTS

- **Upstream project:** `myshell-ai/MeloTTS`
- **Upstream URL:** https://github.com/myshell-ai/MeloTTS
- **License:** MIT
- **Vendored location:** `services/src/airunner_services/vendor/melo/`
- **Pin:** Vendored from the upstream `main` branch at the time the TTS
  runtime was integrated into AIRunner (issue #2051). The exact vendored
  commit is not re-pinned automatically; treat the directory as a snapshot
  that must be reviewed and updated deliberately. See the directory
  [`README.md`](services/src/airunner_services/vendor/melo/README.md).
- **License file:** `services/src/airunner_services/vendor/melo/LICENSE`

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
- **Vendored location:** `services/src/airunner_services/vendor/openvoice/`
- **Pin:** Vendored from the upstream `main` branch at the time the OpenVoice
  TTS runtime was integrated into AIRunner (issue #2051). The exact vendored
  commit is not re-pinned automatically; treat the directory as a snapshot
  that must be reviewed and updated deliberately. See the directory
  [`README.md`](services/src/airunner_services/vendor/openvoice/README.md).
- **License file:** `services/src/airunner_services/vendor/openvoice/LICENSE`

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
- `services/src/airunner_services/vendor/melo/text/tone_sandhi.py` — retains
  an Apache-2.0 header from its upstream origin within the MIT-licensed
  MeloTTS project.
- `src/airunner/components/downloader/gui/windows/setup_wizard/model_setup/stt/templates/whisper_license_ui.py`
  — embeds the Whisper license text for display in the GUI setup wizard.

This section is informational only; the CI check applies to vendored package
directories.
