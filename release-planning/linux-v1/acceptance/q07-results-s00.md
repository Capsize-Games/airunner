# Q07-S00 evidence — 2026-10-09 (PASS on fixed candidate)

Scenario: `q07-gpu-lifecycle.md` Q07-S00 (record candidate, hardware,
driver, model revisions). Operator: agent boot probe on the build box.
Verdict: **PASS** — the frozen daemon boots and serves. The original
FAILED run is retained in git (commit `659d0c564`, defect #2245);
this reruns the scenario from the top against the fixed candidate
with fresh digests.

## Candidate identity

- Bundle dir: `/tmp/bundle/dist/airunner-daemon` (9.9G)
- Entry: `airunner_services.daemon:main`, frozen with
  `pyinstaller==6.12.0`, manifest base `0b5c5701d`
  (branch `batch22/frozen-tail`: native-binaries collection plus
  the mslk triton-jit hook)
- `sha256(airunner-daemon)`:
  `6a6f99adc01b75a84adab809d119df88c3aa5413e74a5fae4a37806df9925cef`
- `sha256(bundle-manifest.json)`:
  `140edbbb9283f0e20286fd13f85844451b3ec90607b0c876914da0cc5c531de3`
- Inspector: exit 0 ("assembled and inspected", 11769 files), two
  expected release-provided-sidecar warnings
  (llama-server, whisper-server)
- Frozen payload proof: `_internal/mslk/mslk.so` (257M),
  `_internal/mslk/quantize/triton/fp8_quantize.py` as source (absent
  from the PYZ), 17 `llama_cpp/lib/*` files including versioned
  SONAMEs, 15 `torchcodec/libtorchcodec_*.so`

## Hardware and driver

- nvidia-smi (observed): NVIDIA GeForce RTX 5080, 16303 MiB,
  driver 615.71.09
- Daemon `/api/v1/daemon/hardware` (observed, 200): 15.56 GB total
  VRAM / 12.89 GB available, CUDA available, compute capability
  12.0, 16 CPUs, Linux

## Boot probes (observed)

Loopback test config (127.0.0.1:18289, scratch
`AIRUNNER_BASE_PATH`, empty models), two consecutive boots:

- Boot 1: `/health` 200 `{"status":"ready",...}` on first poll;
  `/api/v1/daemon/hardware` 401 (auth-guarded, proves serving).
- Boot 2 (`AIRUNNER_INSECURE_NO_AUTH=1`, loopback probe only):
  `/health` 200 and `/api/v1/daemon/hardware` 200 with the
  profile above.
- Both boots: zero `ERROR`/`Traceback`/`CRITICAL` lines;
  `Successfully loaded: 'mslk.so'` in the log; transformers,
  torchao, and the triton-jit `fp8_quantize` module import cleanly.
- Raw evidence: `/tmp/q07-frozen4/{daemon.yaml,
  stdout-first-boot.log,stdout.log,health.json,hardware.json}`,
  build log `/tmp/bundle/build-b4.log`. Probe daemons killed
  after each run; port verified free.

## Downstream

S00 unblocks S01–S08, which remain PENDING.
