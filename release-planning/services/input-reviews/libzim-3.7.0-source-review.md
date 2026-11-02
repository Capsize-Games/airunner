# libzim 3.7.0 source and native replacement review

## Disposition

The unmodified upstream Python distribution is `libzim==3.7.0`. Its Linux CPython
3.13 wheel is SHA-256
`6abe60b6542f95f920d713ef468382942f64787adac07e9b66bc76be0b97f48b`; its
bundled `libzim.so.9` is SHA-256
`6938f3874c6b84a749ea996cbae7d40408252ffb271597b390420dc25b11606e`. That
binary matches the `libzim.so.9.3.0` member from the upstream openZIM
`libzim` 9.3.0 Linux archive byte-for-byte. The wheel does not establish the
exact versions of every statically linked Xapian, ICU, Zstandard, XZ, zlib,
and UUID component.

The unmodified Python wrapper's source build hook downloads a native archive
over HTTP and extracts it without checking a digest. The hook was inspected
but never executed. A hardening patch was merged into the owner-controlled
private wrapper copy and tagged `v3.7.0-capsize.1`; the merged commit is
`09a7857f8526715a52f9e65f37fbdbb1a5f673b7`, and the source tree is
`620a738df0de9f784a2b85193a5ce1538c43ae8d`. The patch requires HTTPS and a
verified SHA-256 before extraction, pins the reviewed x86_64 archive digest,
and includes focused build-hook tests. A second private PR updated the package
version to `3.7.0+capsize.2` and pinned the reviewed setuptools and wheel build
tools. PR #2 merged as `854ffa91605d6406517147ca05f3878b840c8727`; the merged
tree is `e8c1c25f966db52f9599b6c63bc393965d247eb5`. Annotated tag
`v3.7.0-capsize.2` and its private release are published. Private-copy
Actions remain disabled.

An independent Linux x86_64 native candidate was built from openZIM `libzim`
9.3.0 source with pinned, reviewed dependency sources. This candidate links
fixed Xapian 1.4.32 and ICU 79.1; the older kiwix-build recipe selected
Xapian 1.4.23 (affected by CVE-2026-77643) and ICU 73.2 (affected by
CVE-2025-5222). Those older inputs were quarantined from the candidate.
Zstandard 1.5.4 and XZ 5.2.11 are retained from the exact libzim Meson wrap
pins. Static zlib 1.3.1 and UUID from util-linux 2.41.5 were built from the
included Debian source packages as PIC archives.

The candidate native artifact is
`/tmp/build-libzim-9.3.0/src/libzim.so.9.3.0`, SHA-256
`b71f24d6b402e313741c055299e2e046698e8c2eefff57c879fc6a96509e2cde`.
The native test suite passed **28/28**, using `meson test -C
/tmp/build-libzim-9.3.0 --print-errorlogs`. The build used
`-Dtest_data_dir=none`, so it did not run tests requiring external corpus
data.

The patched Python extension was built in a separate uv environment from the
private wrapper tag using Cython 3.0.11 and the previously reviewed
hash-pinned `setuptools==84.2.1`, `wheel==0.48.0`, and `packaging==26.3`
tools. The Cython artifacts matched official PyPI hashes: wheel
`0e25f6425ad4a700d7f77cd468da9161e63658837d1bc34861a9861a4ef6346d`, sdist
`7146dd2af8682b4ca61331851e6aebce9fe5158e75300343f80c07ca80b1faff`. The
Actions-disabled private Cython copy has tag `3.0.11` at upstream commit
`bb4180ad2451845d4187f6a1b6441bc2cda81af8`. PyPI listed no vulnerability
records for this release at review time. The wheel's 302 RECORD-covered files
were checked; it has no `.pth` files or wheel-installed scripts. Inspected
source and license paths in its sdist match the private Git tag byte-for-byte.

The wrapper wheel is `libzim-3.7.0+capsize.2-cp313-cp313-linux_x86_64.whl`, SHA-256
`7747d1dd9f1a0bfa5ee2af9cefdb13c237b8f1eb75874d5c1cba2a19eba36f46`,
21,614,078 bytes. The corresponding source bundle is bound to wrapper source
tree `e8c1c25f966db52f9599b6c63bc393965d247eb5` and private tag
`v3.7.0-capsize.2`. Its 19 RECORD-covered files verified, and its bundled
native library hash matches the candidate. It was built with
`DONT_DOWNLOAD_LIBZIM=1`, an empty environment, and package indexes disabled.
The extension's RUNPATH is `$ORIGIN/libzim/`.

The wheel imported successfully. An entirely synthetic ZIM was created,
opened, read, and full-text searched. The service path
`iter_document_batches_from_file` read that archive and returned article text
with `zim_file` and `zim_path` metadata. That service probe prepended the
separate runtime environment containing the exact candidate wheel; the loaded
extension path and wheel hash are recorded in the candidate build receipt. A
focused upstream wrapper test selection passed **12 tests**. No real ZIM corpus
was used.

The wheel was built on Debian 13 with glibc 2.41 and has a generic
`linux_x86_64` tag, so it is an isolated acceptance artifact rather than a
manylinux distribution wheel. ELF inspection found a GLIBC ceiling of 2.32
and GLIBCXX ceiling of 3.4.32 for the wrapper extension, and GLIBC ceiling of
2.39 and GLIBCXX ceiling of 3.4.32 for bundled libzim. The native library
depends dynamically only on the system C/C++ runtime libraries; its ICU,
Xapian, Zstandard, XZ, zlib, and UUID code is statically linked. The symbols
fit the Ubuntu 24 builder baseline (glibc 2.39). Import/create/read/search was
run locally on Debian 13/glibc 2.41 and passed. The probe verifies loaded extension/native hashes against exact wheel members
and computes numeric symbol-version ceilings; this corrects an earlier
lexicographic maximum reported as GLIBC 2.14. The new
`.github/workflows/libzim-candidate-validation.yml` job performs the actual
Ubuntu 24.04 runtime check; that job has not run yet. A local Ubuntu 24
container attempt failed before startup because Docker's backing store reports
an I/O error for a content blob. The candidate remains separate from the
selected public wheel.

## Source and build evidence

The complete source and build-input bundle is
[`package/source-bundles/libzim-3.7.0-native-9.3.0`](../../../package/source-bundles/libzim-3.7.0-native-9.3.0).
Its `source-manifest.json` provides exact input hashes and provenance;
`candidate-build-receipt.json` records the native output hash and test
result; `BUILDING.md` describes the offline build. The bundle contains the
patched wrapper source, native libzim source, XZ, Zstandard, ICU, Xapian,
Debian zlib and util-linux source packages, and byte-preserved license texts.

Reviewed public Git sources have private maintenance copies with
Actions disabled: `Capsize-Games/python-libzim-maintenance` (wrapper patch),
`Capsize-Games/libzim-maintenance` (native source),
`Capsize-Games/kiwix-build-maintenance` (the pinned build action, reviewed as
data only), `Capsize-Games/xapian-core-maintenance`, and
`Capsize-Games/libzim-build-inputs-maintenance`. No automatic synchronization
is enabled. The original kiwix-build archive action downloads from
`tmp.kiwix.org` and extracts without an expected digest; it was not run.

The reproducible native candidate build used GCC/G++ 13.3, Meson 1.12.1,
Ninja 1.12.1, and Python 3.13.5. Native sources were built offline and with
one build job. The build used no test data downloads. The wrapper's focused
build-security tests passed **5/5** in the existing `.venv-ci`;
`compileall` and `git diff --check` also passed in its private source copy.
The patched wheel build used the hash-pinned Cython and already-reviewed
backend tools in a new uv environment; no existing project environment was
modified.

## License handling

The Python wrapper declares GPL-3.0-or-later. Native libzim and Xapian declare
GPL-2.0-or-later. ICU 79.1's original license, Zstandard's LICENSE and
COPYING files, XZ's GPL/LGPL texts, zlib's license, and util-linux's UUID
license text are preserved from their corresponding source inputs in the
bundle. No copyright statement was invented. The source bundle is provided
for the replacement candidate; the existing selected wheel must retain its
own notices and is not represented as having been rebuilt from these inputs.

## Distribution work still required

Run the Ubuntu 24.04 candidate-validation workflow and record its uploaded
receipt. If that target check fails, rebuild or correct the candidate before
considering it for the dependency lock. The wheel has a unique internal version
and matching private source tag/release; it remains separate from the selected
dependency wheel until the target check and remaining service acceptance are
complete.
