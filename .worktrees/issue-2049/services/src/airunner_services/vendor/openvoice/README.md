# Vendored OpenVoice code

This directory contains vendored code from the upstream
[OpenVoice](https://github.com/myshell-ai/OpenVoice) project
(MIT licensed).

## Origin and pin

- **Upstream project:** `myshell-ai/OpenVoice`
- **Upstream URL:** https://github.com/myshell-ai/OpenVoice
- **Pin:** vendored from the `main` branch of the upstream repository at the
  time the OpenVoice TTS runtime was integrated into AIRunner (issue #2051).
  The exact vendored commit is not re-pinned automatically; treat this
  directory as a snapshot that must be reviewed and updated deliberately.

## Local modifications

The vendored files are intentionally kept close to upstream so that merging
upstream fixes stays feasible. AIRunner applies the following local changes:

- **Supply-chain hardening:** `torch.load` calls load checkpoints with
  `weights_only=True` where supported (issue #2036).
- **Path resolution:** model and cache paths resolve through
  `airunner_services.vendor.openvoice.api` helpers so the vendored code stays
  relocatable across machines and containers.

## Licensing

The upstream OpenVoice project is MIT licensed (`Copyright 2024 MyShell.ai`).
The AIRunner project does not own the copyright to the upstream files in this
directory.

- The MIT license text and the upstream copyright notice live in
  [`LICENSE`](LICENSE) in this directory (issue #2059).
- This package is also listed, with its full license text and upstream origin,
  in the top-level
  [`THIRD_PARTY_NOTICES.md`](../../../../../THIRD_PARTY_NOTICES.md)
  (issue #2059).
