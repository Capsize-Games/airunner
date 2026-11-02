# Linux CUDA dependency source review

## Scope

This review covers the 25 CUDA/native runtime inputs resolved from the frozen
candidate constraints SHA-256
`f84c434c6472320c41ed0f7488614096b4c85650973cbbdd0b53d9e853319e24`.
Exact wheel hashes, members, RECORD results, origin indexes, and OSV results are
in the ignored evidence files named below. This is a bounded review of the
selected upstream release metadata, packaging/build hooks, relevant runtime
entry points, notices, and published binary artifacts. It is not a line-by-line
audit of PyTorch or closed NVIDIA binaries.

The eight source repositories were cloned at the exact release revisions,
preserving upstream histories, then copied to owner-private repositories with
GitHub Actions disabled and no automatic sync. The source revisions are:

| Source | Selected release | Exact commit | Owner-private copy |
| --- | --- | --- | --- |
| `pytorch/pytorch` | `v2.13.0` | `cf30153c4c131c8164ee7798e5022d810682e2cb` | `Capsize-Games/pytorch-maintenance` |
| `pytorch/audio` | `v2.11.0` | `34c52a67e8941bbd8e6adaca0eb0b9eabec11d78` | `Capsize-Games/pytorch-audio-maintenance` |
| `pytorch/vision` | `v0.28.0` | `8fb87713a24951e639c494b0f2a8a81b5f8e33a6` | `Capsize-Games/pytorch-vision-maintenance` |
| `triton-lang/triton` | `v3.7.1` | `f797708c0626e5f9840ca5b0a98790e2c7cb09ad` | `Capsize-Games/triton-maintenance` |
| `NVIDIA/cuda-python` | `v12.9.9` | `89713a7c8bf61037f6a0375ab611778c21f6f9cd` | `Capsize-Games/cuda-python-maintenance` |
| `fredrik-johansson/mpmath` | `1.3.0` | `b5c04506ef0cd4a1f1213f8389ee21c9c3551582` | `Capsize-Games/mpmath-maintenance` |
| `networkx/networkx` | `networkx-3.4.2` | `2acf1590f82757c01a57b81b8c5dfb79e60aa416` | `Capsize-Games/networkx-maintenance` |
| `sympy/sympy` | `1.14.0` | `fe935ceb303891d1f8bea4c03b19fd9ec9464b02` | `Capsize-Games/sympy-maintenance` |

The PyTorch tree contains `AGENTS.md`, `CLAUDE.md`, and 14 Claude skill
documents. They were treated as untrusted data and not followed. They describe
project scratch, contribution, build, test, and review workflows; none is
included in the selected wheel. The wheel’s build was not run. PyTorch has 37
submodules, which were not initialized because the reviewed input is its
published wheel. This review does not claim those submodules are source-audited.

## Source and packaging findings

- **PyTorch**: the selected wheel contains its Apache/LLVM-exception/BSD/MIT
  license bundle. The source setup uses CMake and compiler subprocesses. The
  `USE_NIGHTLY` branch downloads a wheel only when the explicit environment
  variable is set. Runtime hub/download APIs are explicit calls. No import,
  build, or hub operation was performed.
- **TorchAudio**: the selected release’s setup file has a helper that can fetch
  archives, but the exact setup entry point does not call it. Its extension
  build uses the PyTorch/CMake toolchain. The wheel includes the project license
  but not the exact source-tree notices for bundled CTC code: BSD-2-Clause
  `src/libtorchaudio/cuctc/LICENSE`, Apache-2.0
  `src/libtorchaudio/cuctc/src/bitonic_topk/LICENSE`, and the
  `third_party/LICENSES_BUNDLED.txt` mapping. The candidate includes these
  exact source notices and the canonical BSD-3-Clause CUTLASS license. The
  mapping identifies `ctc_fast_divmod.cuh` as BSD-3-Clause and says it was
  modified from CUTLASS; the selected CUTLASS submodule revision is recorded,
  but exact file ancestry is not asserted.
- **TorchVision**: source setup probes local system libraries and invokes local
  build tools. Dataset and pretrained-weight downloads are explicit runtime
  APIs. The selected wheel bundles libpng 1.6.56, libjpeg-turbo 3.1.3, libwebp
  1.6.0, SharpYuv 4.0.2, and NVIDIA `libnvjpeg.so.12`. The candidate adds the
  exact upstream license files for zlib 1.3.2, libpng, libjpeg-turbo, and
  libwebp/SharpYuv, plus NVIDIA's CUDA 12.9.1 EULA and wheel-provided notices.
  Source commits and file hashes are in
  `packaging/licenses/torchvision-0.28.0-cu129-supplement/source-notices.json`.
  The binary version mapping is bounded: native version strings and static
  version functions identify these bundled versions, while the closed `nvjpeg`
  patch source was not identified independently. The candidate has regenerated
  RECORD and passed ZIP CRC checks; it is inactive pending whole-graph and
  runtime review.
- **Triton**: exact source `f797708c0626e5f9840ca5b0a98790e2c7cb09ad` pins
  LLVM/MLIR commit `1f126a6dea50d185c0781743a667390037ae88bd`; the wheel's
  `libtriton.so` statically includes that closure. The candidate adds the exact
  LLVM license, Triton's compiled `f2reduce` notice, official CUDA 13.1.1 and
  12.8.1 EULAs, the CUPTI 12.8.1 copyright/license page, and bundled AMD HIP
  header notices. Those files and hashes are recorded in
  `packaging/licenses/triton-3.7.1-supplement/source-notices.json`.
  The first hardened candidate still contains NVIDIA `ptxas`,
  `ptxas-blackwell`, `cuobjdump`, `nvdisasm`, all 154 bundled CUDA headers, and
  nine CUPTI payload files. The selected EULA Attachment A does not list all of
  those members, and no separate grant was found, so that candidate remains
  quarantined. Its added notices do not establish redistribution rights.

  A separate feature-preserving subset recipe now removes those exact 167
  members while retaining Triton's CUDA backend/JIT code and the EULA-listed
  `libdevice.10.bc`. The recipe is
  `package/triton-external-toolchain-subset.json`; it binds the source candidate,
  each excluded member hash, the replacement-tool hashes, and the output wheel
  hash. `scripts/build_triton_external_toolchain_subset.py` verifies input and
  output RECORDs, all excluded-member digests, ZIP CRCs, and the retained
  libdevice digest. The resulting `3.7.1+capsize.2` wheel is 138,821,684 bytes
  with SHA-256
  `a90ecd98dd9aa6207e820396a2e2d5ee5ef9c118cf59d25098955b35f8ac4e93`. It is
  in ignored local evidence and has not been installed, imported, or loaded.

  Triton resolves external overrides for
  `TRITON_PTXAS_PATH`, `TRITON_PTXAS_BLACKWELL_PATH`, `TRITON_CUOBJDUMP_PATH`,
  and `TRITON_NVDISASM_PATH` as external tool paths. It also accepts
  `TRITON_LIBDEVICE_PATH`; `TRITON_CUDACRT_PATH` and `TRITON_CUDART_PATH` are
  added to runtime compiler include paths, and `TRITON_CUPTI_LIB_PATH` selects
  the CUPTI library directory. An absent or invalid tool override falls back to
  the wheel's bundled path; the subset preflight therefore requires and hashes
  all four tool overrides, both header roots, the exact `cuda.h`, and all nine
  CUPTI payload files before service startup. It also rejects an installed
  Triton package that still contains any excluded member, without importing the
  package. The preflight is `scripts/triton_toolchain_preflight.py`.

  Source inspection confirms the JIT uses ptxas below SM100 and
  `ptxas-blackwell` for SM100 and newer. `cuobjdump` backs the disassembly
  helper; `nvdisasm` supports disassembly and line-info paths. The NVIDIA
  runtime extension directly includes `cuda.h`; the selected header has no
  other NVIDIA-header includes, and external CRT/runtime directories are added
  to its include search paths. Proton resolves `libcupti.so` through
  `TRITON_CUPTI_LIB_PATH`. The source contracts support this boundary, but the
  external toolchain has not been installed or runtime-tested on the service
  target. The preflight suite passed 9 tests and the subset builder suite
  passed 5 tests. JIT and `torch.compile` remain in the candidate. No model or
  GPU operation was run.
- **CUDA Python**: selected `cuda-bindings` and `cuda-pathfinder` sources share
  the exact `cuda-python` release tree. The PEP 517 hook delegates metadata to
  setuptools and reads local CUDA headers/compiler configuration to generate
  bindings. It does not download dependencies. The wheels include Apache-2.0
  notices. No hook was executed.
- **mpmath, NetworkX, and SymPy**: exact source trees are pure Python and have
  no native build hooks. Their license files are in the wheels. NetworkX and
  SymPy expose console entry points; those are expected package commands, not
  install-time scripts. No entry point was invoked.
- **CUDA toolkit metadata wheel**: `cuda-toolkit==12.9.1` is a 2,303-byte,
  metadata-only wheel with no license expression or license file. Its separate
  notice supplement preserves the official CUDA 12.9.1 EULA PDF and extracted
  text, each bound by SHA-256 to the exact selected wheel. This resolves the
  missing-notice record; it does not broaden the EULA's listed redistribution
  scope for other toolkit components.
- **NVIDIA vendor libraries**: the selected `nvidia-*` wheels are closed
  vendor binaries. Their source was not present in the selected public source
  trees. The review therefore covers exact wheel contents, license text,
  RECORD, ELF dependencies, versioned system ABI requirements, and RUNPATH
  metadata only. NVIDIA proprietary CUDA EULA text is preserved in the wheels.
  No legal conclusion is made from SPDX metadata alone. NCCL's selected wheel
  notice, exact source `LICENSE.txt`, and exact source `ThirdPartyNotices.txt`
  are preserved as separate records because the wheel metadata and notice text
  describe different licensing scopes.

## Artifact inspection

All 25 exact CPython 3.13/Linux x86_64 wheels were downloaded to ignored private
evidence. Their hashes matched the frozen candidate lock. ZIP member paths were
checked for traversal, duplicates, symlinks, and special files. RECORD hashes
and sizes validated for every original wheel. OSV’s exact-version batch query
returned zero advisories for the selected versions on 2026-11-02; this is not a
claim that the artifacts are free of vulnerabilities.

Static `readelf` inspection covered 115 ELF members without loading them. The
maximum recorded symbol versions are `GLIBC_2.28` and `GLIBCXX_3.4.22`. This
describes the inspected binary floors; it does not establish runtime
compatibility or GPU functionality.

The initial wheels contain absolute ephemeral paths in three TorchAudio
extensions, TorchVision `_C.so`, both Triton MLIR dialect plugin names, the
Triton test plugin, and two optional NVSHMEM bootstrap plugins. The TorchAudio
and TorchVision paths pointed into temporary build environments. Triton’s
plugin paths also pointed into an LLVM cache and a build directory. The
NVSHMEM MPI and SHMEM bootstrap paths pointed into an OpenMPI build directory.
The two NVSHMEM plugins are optional MPI/SHMEM bootstrap components; this does
not make their absolute paths acceptable for distribution.

An owner-private Patchelf 0.18.0 source copy was created at
`Capsize-Games/patchelf-maintenance` (upstream commit
`99c24238981b7b1084313aca8f5c493bb46f302c`, Actions disabled). The reviewed
tool is a standalone C++ ELF editor; the selected source and build path showed
no network or process-launch hooks. Its GPL-3.0 `COPYING` remains in the private
source copy. An offline local build used:

```text
g++ -std=c++17 -D_FILE_OFFSET_BITS=64 -O2 -Wall -Wextra -Wcast-qual src/patchelf.cc -o patchelf
```

The candidate-only wheel set in the ignored
`cuda-native-runpath-candidates/` directory changes the listed runtime paths and local distribution versions, and adds
the exact supplemental license payloads described above. It preserves each ELF’s `DT_NEEDED`, SONAME, and
original `DT_RPATH`/`DT_RUNPATH` kind. Wheel versions, dist-info paths, RECORDs,
and candidate SHA-256 values were regenerated and checked. Static inspection
found no remaining absolute RPATH/RUNPATH in the three ELF-hardened candidates.
The NVSHMEM subset candidate does not modify any vendor ELF bytes; it excludes
only the opt-in MPI and SHMEM bootstrap plugins and recomputes local wheel
metadata. The original vendor wheel and excluded members remain unchanged in
private evidence. The exact NVSHMEM source license supplement is preserved as a
separate notice. These candidates remain inactive pending parent review and
runtime acceptance.

## Per-package inventory and disposition

The exact version and original artifact hash for every pin are in
`cuda-native-wheel-review.json`; each row in the ignored
`cuda-native-source-review.json` records its source or artifact-only review
basis and current disposition. The package set is:

| Package | Selected version | Review disposition |
| --- | --- | --- |
| `cuda-bindings` | `12.9.9` | Exact source and Apache-2.0 wheel reviewed; runtime/hardware behavior not exercised. |
| `cuda-pathfinder` | `1.8.3` | Exact source and Apache-2.0 wheel reviewed; path search behavior is local. |
| `cuda-toolkit` | `12.9.1` | Official CUDA 12.9.1 EULA supplement is preserved; metadata-only wheel remains statically reviewed. |
| `mpmath` | `1.3.0` | Exact pure-Python source and BSD license reviewed. |
| `networkx` | `3.4.2` | Exact pure-Python source and license file reviewed; console entry point not run. |
| `nvidia-cublas-cu12` | `12.9.1.4` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cuda-cupti-cu12` | `12.9.79` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cuda-nvrtc-cu12` | `12.9.86` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cuda-runtime-cu12` | `12.9.79` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cudnn-cu12` | `9.20.0.48` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cufft-cu12` | `11.4.1.4` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cufile-cu12` | `1.14.1.1` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-curand-cu12` | `10.3.10.19` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cusolver-cu12` | `11.7.5.82` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cusparse-cu12` | `12.5.10.65` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-cusparselt-cu12` | `0.8.1` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-nccl-cu12` | `2.29.7` | Wheel notice plus exact source LICENSE and ThirdPartyNotices are preserved separately; no licensing conclusion is inferred from metadata. |
| `nvidia-nvjitlink-cu12` | `12.9.86` | Closed NVIDIA binary; exact wheel and proprietary notice reviewed statically. |
| `nvidia-nvshmem-cu12` | `3.4.5+capsize.1` candidate | Local subset candidate excludes only opt-in MPI/SHMEM bootstrap plugins, with no ELF edits; original wheel remains preserved. Candidate inactive. |
| `nvidia-nvtx-cu12` | `12.9.79` | Closed NVIDIA binary; Apache-2.0 notice and exact wheel reviewed statically. |
| `sympy` | `1.14.0` | Exact pure-Python source and BSD license reviewed; console entry point not run. |
| `torch` | `2.13.0+cu129` | Exact source and wheel metadata reviewed; wheel ships its license bundle; no build/import/GPU run. |
| `torchaudio` | `2.11.0+cu129.capsize.1` candidate | Local candidate fixes three RPATHs and adds exact CTC/CUTLASS notices; static-only, inactive. |
| `torchvision` | `0.28.0+cu129.capsize.1` candidate | Exact image-library source notices and CUDA EULA added; candidate is static-only and inactive. Closed `nvjpeg` source mapping remains bounded as described above. |
| `triton` | `3.7.1+capsize.2` candidate | Candidate removes unlisted tool/header/CUPTI payloads, retains JIT and permitted libdevice, and requires exact preflighted external equivalents. Static candidate checks and focused tests passed; no external runtime or GPU validation. Inactive. |

## Commands and exclusions

The original wheels were downloaded and statically inspected; source files were
read from the exact revisions above. `readelf`, ZIP/RECORD validation, OSV
metadata, and local Patchelf candidate checks ran. No dependency was installed
into the project environment, imported, loaded with `dlopen`, or exercised on a
GPU. No model was downloaded or run. No selected runtime package build hook or source build was
executed; the reviewed Patchelf build tool was compiled as described above. The full source review is bounded to the files and artifact metadata
described above; it does not claim a complete semantic review of all source or
vendor binaries.

Private evidence paths:

- `.headlesscode/service-audit-2026-11-02/linux-release-lock/cuda-native-source-intake.json`
- `.headlesscode/service-audit-2026-11-02/linux-release-lock/cuda-native-wheel-review.json`
- `.headlesscode/service-audit-2026-11-02/linux-release-lock/cuda-native-osv-review.json`
- `.headlesscode/service-audit-2026-11-02/linux-release-lock/cuda-native-elf-review.json`
- `.headlesscode/service-audit-2026-11-02/linux-release-lock/cuda-native-source-review.json`
- `.headlesscode/service-audit-2026-11-02/linux-release-lock/cuda-native-runpath-candidates/manifest.json`

The current input manifest SHA-256 is
`715e49adc27227beb719e9419dc9c0a4e2bbfdadfc2a3bc3cc93a1eb9b3d1e15`. The local repeat-transform report SHA-256 is
`003eecb23fae5da6257c86746bed63add471c06620f1dc61c0ba841df929e901`. Two
independent offline transforms produced identical wheel hashes. The candidates
are not active lock inputs, were not installed or imported, and have not been
loaded with `dlopen` or exercised on CUDA hardware. Triton `.1` remains
unsuitable for redistribution because it contains the bundled NVIDIA
tool/header/CUPTI payload. The separate `.2` subset removes those members; it
is still inactive pending external-toolchain integration and runtime
validation.

The hosted candidate workflow explicitly selects TorchAudio, TorchVision and
NVSHMEM only, with their accompanying notice files. Triton is excluded from
public candidate artifact uploads while the `.2` external-toolchain contract
awaits integration and runtime validation. The `.1` wheel remains quarantined.
This partial artifact build does not satisfy the full ML release requirement.

The Triton subset recipe SHA-256 is
`ff68281c53526986f054b52d66211dd6f771085e0e0230331430698a7e953958`; its
ignored candidate report records output SHA-256
`a90ecd98dd9aa6207e820396a2e2d5ee5ef9c118cf59d25098955b35f8ac4e93`, 167
excluded NVIDIA members, regenerated RECORD, and successful ZIP CRC validation.
The fail-closed preflight requires exact external tool, CUDA header, and CUPTI
hashes, and verifies that the installed package omits all 167 members.

The hosted staging URLs are the exact links from the official PyTorch CUDA
index, including its `download-r2.pytorch.org` and NVIDIA PyPI destinations.
The original handoff URLs returned HTTP 403; the corrected recipe preserves
the same reviewed source wheel SHA-256 values.

The hosted compile exposed two required repository headers. The builder now
stages and verifies `src/patchelf.cc`, `src/patchelf.h` and `src/elf.h` from
the exact reviewed Patchelf revision before and after compilation. The header
review covers ELF data definitions and editor templates, their includes and
process/network primitives; it is not an exhaustive semantic audit of the
compiler or system C++ headers. No upstream bootstrap hook is run.
