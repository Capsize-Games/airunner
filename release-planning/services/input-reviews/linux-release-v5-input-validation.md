# Linux release V5 input validation

The selected build input lock covers `./services[linux-release]` for CPython
3.13.5, Linux x86_64 and CUDA 12.9. It contains 243 exact versions and one
reviewed wheel hash per version. Its SHA-256 is
`63461b6a5fe1cd72e689ccf459a86f8d98f5cce78bd41b0c6351a71e521ed006`.
The historical desktop lock is retained separately. OpenVoice, Melo and the
quarantined TTS vendor are excluded.

V5 changes one V4 artifact: `llama-cpp-python==0.3.21+capsize.3`, SHA-256
`3732bbd0f9f2a79d7dc69ff0558ca9d228f69408c0c66461ca5f993638485e3a`.
The other 242 selected wheels are unchanged. The visible package inventory and
owner origin exception are recorded in `../DEPENDENCY_DECISIONS.md`.

Validation completed on 2026-11-03 UTC:

- The production artifact stager retrieved and verified all 243 wheels from
  the canonical URLs, committed wheelhouse and bound GitHub Actions artifacts.
  The staged requirements match the selected lock byte for byte. No package
  was installed or imported by that stager.
- A fresh project environment installed all 243 exact wheels with `uv`,
  hash enforcement, wheel-only inputs, no dependency resolution/builds and
  kernel network denial. `uv pip check` passed.
- Installed metadata satisfies all 77 direct service base/profile requirements.
- The production notice collector and verifier passed: 243 distributions,
  1,734 notice files, no reported problems. The frozen bootloader's separate
  GPL notice and exception are also required by the bundle specification.

Detailed receipts remain in the ignored service audit directory. The original
V4 staging attempt that used a malformed lock and the first V5 staging attempt
that used an unsupported manifest status are retained as failed evidence;
neither was used for installation.

`lock_status: ready` means the reviewed inputs are available to candidate
builds. It does not establish model, GPU, authenticated API, frozen-artifact,
installation or release acceptance. The Actions inputs are temporary; their
durable release mirrors remain required before final publication. Required CI,
service acceptance, mainline integration and immutable tag/release are still
tracked by the service project.
