# P04: Qt packaging comparison and recipe decision

Issue: [P04](https://github.com/Capsize-Games/airunner/issues/2103)
([parent spec](https://github.com/Capsize-Games/airunner/issues/2083)).
Work type: isolated evidence-gathering. Base commit `742a686c2` plus the
uncommitted P02 profile context (`setup.py`, `services/setup.py`,
`package/constraints-linux-nvidia-cu129.txt`), which this issue reads
but does not modify.

## Decision

**Use directory-mode PyInstaller (`pyinstaller==6.12.0`) as the one
supported bundle recipe.** Do not adopt pyside6-deploy/Nuitka.

The comparison below was run as written (Qt entry point, resources,
one runtime with a double), but the choice is weighted toward the
services-only release scope: the shipped Linux v1 artifact is the
services bundle with no Qt desktop in it (`services/setup.py`
`desktop` aggregate "intentionally carries no Qt/PySide6 payload").
PyInstaller directory-mode serves both the Qt desktop and the Qt-free
services bundle with one recipe (proven below: 197M Qt dir and 40M
Qt-free dir from the same tool); pyside6-deploy is Qt-specific and
buys the services artifact nothing while adding a C toolchain,
an older imposed Nuitka, and a onefile default that conflicts with
the directory-bundle architecture (spec item 9).

GUI/hardware launch was not performed: no GUI or model launch is
permitted in an ordinary coding session. Choice rests on actual
artifact inspection; GUI startup and target-hardware verification
remain pending owner verification (see "Not verified").

## Experiment setup (isolated build environment)

Worktree-local venv only (`.venv`, via `uv venv --seed`, CPython
3.13.5, pip 26.2.1). The owner's venvs were not touched. Build tool
pins installed into the isolated venv:

```
pyinstaller==6.12.0          # already the pinned dev requirement
PySide6==6.9.0               # release GUI pin (+ Addons/Essentials/shiboken6)
Nuitka==4.2.2                # installed for parity, then replaced by the tool
patchelf==0.19.1.0           # Nuitka standalone prerequisite (PyPI wheel)
tomlkit==0.15.1              # missing pyside6-deploy dependency, added by hand
```

Final freeze after the runs (note Nuitka 2.6.8 — see Candidate B):

```
altgraph==0.17.5 Nuitka==2.6.8 ordered-set==4.1.0 packaging==26.3
patchelf==0.19.1.0 pyinstaller==6.12.0 pyinstaller-hooks-contrib==2026.8
PySide6==6.9.0 PySide6_Addons==6.9.0 PySide6_Essentials==6.9.0
setuptools==84.0.0 shiboken6==6.9.0 tomlkit==0.15.1 zstandard==0.25.0
```

Host: Linux x86_64, gcc 14.2.0. No system packages were installed;
`patchelf` was absent from PATH, so the PyPI wheel supplied it.

Representative probes (full source in the Appendix; never executed —
bundled and inspected statically only, per the no-GUI-launch
guardrail). They mimic the bundler-relevant dimensions of
`src/airunner/launcher.py` without importing the app (which would
drag torch and the 352-pin P02 closure into the experiment):

- `p04_qt_probe.py`: `QApplication`/`QTranslator` startup path,
  `QLibraryInfo` plugin path, one `importlib.resources` data load
  (stands in for `translations/*.qm`, `styles/**`, `gui/images`,
  agreement `.md`, `static/**` from `setup.py package_data`),
  plus one runtime-double import.
- `p04_runtime_double.py`: sidecar-discovery double (manifest dict +
  `discover_sidecar()`), no hardware/model/subprocess/network
  behavior. Stands in for one native runtime.
- `probe_data/sample.qss` + `probe_data/__init__.py`: data package
  referenced only through the runtime string
  `resources.files("probe_data")` — the hard case for static
  bundlers, and the shape several airunner resource loads take.
- `p04_headless_probe.py`: Qt-free console entry importing only the
  runtime double. Stands in for the services daemon dimension.

## Candidate A: PyInstaller directory-mode (chosen)

Exact build command (run from `/tmp/p04-builds`):

```bash
.venv/bin/pyinstaller --onedir --noconfirm --clean \
  --name p04_qt_pyinstaller --paths /tmp/p04-builds/probe_src \
  --distpath /tmp/p04-builds/dist-pyinstaller \
  --workpath /tmp/p04-builds/work-pyinstaller \
  /tmp/p04-builds/probe_src/p04_qt_probe.py
```

Result: exit 0. Cold build ~25s (analysis through COLLECT per the
build log); a clean re-run to a second distpath took 9s and
reproduced the same 197M total — the recipe reproduces.

Artifact identity: `dist-pyinstaller/p04_qt_pyinstaller/`, 197M,
260 files. Exe `p04_qt_pyinstaller` is ELF 64-bit x86-64,
sha256 `b3b541e0…` (first 32 hex), dynamically linked against
system libc/zlib/pthread only (`ldd` shows no bundled-lib
dependence for the bootloader itself).

Inspection findings:

- Qt plugins: complete set under `_internal/PySide6/Qt/plugins/`,
  including `platforms/` with all 10 platform plugins
  (`libqxcb.so`, `libqoffscreen.so`, `libqminimal.so`,
  `libqwayland-*`, …). Collected automatically by PyInstaller's
  `hook-PySide6*.py` hooks plus the `pyi_rth_pyside6` runtime hook
  (all visible in the build log).
- Qt translations: 92 `.qm` files bundled by default under
  `PySide6/Qt/translations/` — relevant because airunner ships its
  own `translations/*.qm` (issue #2043); the mechanism includes
  translation payloads without extra flags.
- Static app import: `p04_runtime_double` present in `PYZ-00.pyz`
  (verified in `PYZ-00.toc`) — the runtime double ships.
- Runtime-string data: `probe_data` is ABSENT (zero hits across all
  five `.toc` files). `resources.files("probe_data")` is invisible
  to static analysis, so the data package needs an explicit
  `--add-data` / spec `datas` entry. Same gap class as airunner's
  path-loaded resources; it is a recipe constraint, not a
  disqualifier — the declaration mechanism exists and is simple.
- Missing-import report: `warn-p04_qt_pyinstaller.txt`, 23 lines,
  benign only — `winreg`, `nt`, `_winapi`, `msvcrt`
  (platform-conditionals), `_frozen_importlib_external` and a
  `collections.abc` quirk. No app-level missing module. This
  machine-readable report is the natural input to a release gate in
  the spirit of `scripts/check_artifact_imports.py`.
- Target sysdeps: `ldd` on the bundled `libqxcb.so` reports zero
  "not found" entries on this workstation. The XCB system-library
  tail still needs confirming on the Ubuntu 24.04 baseline by the
  owner (see "Not verified").

## Candidate B: pyside6-deploy / Nuitka (rejected)

Exact build command (run from `/tmp/p04-builds/nuitka-proj`
containing copies of the Qt probe, the runtime double, and
`probe_data/`, with the venv `bin/` on PATH for `patchelf`):

```bash
pyside6-deploy -f --keep-deployment-files --name p04_qt_nuitka p04_qt_probe.py
```

Result: exit 0 in ~3 minutes (spec written 16:05:52, output binary
16:08:50), but with three findings against adoption:

1. **The tool mutated the build environment.** It uninstalled the
   installed Nuitka 4.2.2 and installed its pinned `Nuitka==2.6.8`
   (recorded in `pysidedeploy.spec` as `packages = Nuitka==2.6.8`),
   building that older Nuitka's wheel from sdist mid-run. A release
   recipe whose tool downgrades its own backend is the opposite of
   a frozen toolchain. It also required `tomlkit`, which PySide6
   6.9.0 does not declare, failing with `ModuleNotFoundError`
   until installed by hand.
2. **It defaults to onefile, not a directory bundle.** The top-level
   output is a single 44M `p04_qt_nuitka.bin` self-extractor (links
   only libc; unpacks to temp at every startup). The underlying
   standalone directory exists only as an intermediate
   (`deployment/p04_qt_probe.dist/`, kept here via
   `--keep-deployment-files`): 160M, 79 files. Directory mode is
   opt-in (`mode = standalone` in `pysidedeploy.spec`), while the
   architecture decision and the P05/P07 bundle/upgrade story need
   a directory as the primary artifact. Startup unpacking also
   works against transactional upgrades.
3. **Quieter failure surface.** Nuitka ran with `--quiet`; no
   missing-module report is surfaced (the deploy log is 39 lines,
   mostly the Nuitka reinstall). Inclusion had to be verified by
   `strings` on the binary (`p04_runtime_double`: 5 hits —
   compiled in; `probe_data`: name-string hits only, data files
   absent — the same runtime-string gap as Candidate A, with no
   report pointing at it).

Other `.dist` inspection notes: Qt plugins present but at the
nonstandard Nuitka layout `PySide6/qt-plugins/platforms/libqxcb.so`
(works via Nuitka's Qt handling, but every plugin-path assumption
must be re-verified); app translations excluded by the tool's own
default (`extra_args = --quiet --noinclude-qt-translations`), so
airunner's `.qm` payload would need explicit re-inclusion; C build
used `ccache`, adding cache-state to reproducibility.

The 160M-vs-197M size difference does not outweigh the above: both
are dominated by the same Qt 6.9 shared libraries, and size is not
the release's binding constraint.

## Services-dimension probe (supports the weighting)

The Qt-free probe through the same PyInstaller recipe:

```bash
.venv/bin/pyinstaller --onedir --noconfirm --clean \
  --name p04_headless_pyinstaller --paths /tmp/p04-builds/probe_src \
  --distpath /tmp/p04-builds/dist-pyinstaller-headless \
  --workpath /tmp/p04-builds/work-pyinstaller-headless \
  /tmp/p04-builds/probe_src/p04_headless_probe.py
```

Result: exit 0 in 4s. Artifact: 40M, 3 files (exe,
`_internal/base_library.zip`, `_internal/libpython3.13.so.1.0`),
zero Qt/PySide6/XCB payload (case-insensitive filename search over
the tree is empty). Warn file carries the same benign-only set as
the Qt build. This is the shape the services-only release bundle
takes under the chosen recipe: one tool, no Qt tax, no second
toolchain to freeze.

## Comparison summary

| Dimension | PyInstaller onedir (A) | pyside6-deploy/Nuitka (B) |
|---|---|---|
| Build result | exit 0, ~25s cold / 9s warm | exit 0, ~3min incl. backend rebuild |
| Qt dir size / files | 197M / 260 | 160M / 79 (+44M onefile wrapper) |
| Qt plugins | full set, standard layout | present, Nuitka layout |
| Qt translations | 92 `.qm` included by default | excluded by tool default |
| Static runtime-double import | in PYZ (toc-verified) | frozen into binary (strings-verified) |
| Runtime-string data files | missing unless declared | missing unless declared |
| Missing-import report | warn file, benign-only | none surfaced (`--quiet`) |
| Default output mode | directory available directly | onefile; directory opt-in |
| Build prerequisites | none beyond pip | C compiler, patchelf, ccache state |
| Environment hygiene | no mutation | downgraded Nuitka 4.2.2 to 2.6.8 |
| Headless/services fit | 40M Qt-free dir, same recipe | Qt-oriented wrapper; no services value |

## Reproducible recipe (chosen candidate)

Pinned tool: `pyinstaller==6.12.0` (already pinned in the
`DEVELOPMENT_REQUIREMENTS` of `setup.py`, `services/setup.py`, and
`native/setup.py`). P05 owns the full-application spec; the recipe
contract it must implement is:

```bash
# From the repo root, in an isolated venv with the P02 profile
# installed (package/constraints-linux-nvidia-cu129.txt):
pyinstaller --onedir --noconfirm --clean \
  --name airunner \
  --paths src \
  --add-data "src/airunner/translations:airunner/translations" \
  --add-data "src/airunner/gui/styles:airunner/gui/styles" \
  --add-data "src/airunner/gui/images:airunner/gui/images" \
  --add-data "src/airunner/gui/resources:airunner/gui/resources" \
  --collect-data airunner \
  src/airunner/launcher.py
# Then gate on the warn file: fail the build on any missing module
# outside the reviewed platform-conditional set (see evidence above).
```

Data-file rule (from the `probe_data` finding): every resource the
app loads by runtime path/string — `translations/*.qm`,
`components/**/templates/*.ui`, agreement `.md`, `static/**` (all
listed in `setup.py package_data`) — needs an explicit `datas`
entry; static-import collection alone is insufficient. P05 must
verify each entry by filename search over the built dir, as done
for the probes here.

Manifest contract: every bundle ships a `bundle-manifest.json`
beside the executable, using the shape already established by
`scripts/package_desktop_client.py`
(`{bundle, index, files:[{path, sha256}]}`), extended with the
build identity:

```json
{
  "bundle": "airunner",
  "tool": "pyinstaller==6.12.0",
  "entry": "src/airunner/launcher.py",
  "base": "742a686c2",
  "files": [{"path": "airunner", "sha256": "<hex>"}]
}
```

Probe manifest records (this experiment): Qt dir 197M/260 files
with exe sha256 `b3b541e0…`; re-run reproduced 197M; headless dir
40M/3 files with no Qt payload. Raw logs and trees were kept at
`/tmp/p04-builds/` for the session (build logs, `.toc` files,
warn files, both `.dist` trees) and are not committed; the probe
sources in the Appendix plus the commands above reproduce them.

## Startup constraints found

- Data files referenced by runtime strings are silently absent
  from both candidates unless declared (proven for `probe_data`).
  The chosen recipe handles this with `datas` entries; the gate
  is a filename search over the built dir, not a launch.
- The Qt platform plugin needs host XCB libraries at startup.
  Zero are missing on this workstation, but the Ubuntu 24.04
  baseline still needs owner confirmation (below).
- The Nuitka path additionally needs a C compiler, `patchelf`,
  and (for sane rebuild times) `ccache` in the build environment,
  plus an explicit `mode = standalone` override and translation
  re-inclusion — all avoided by the chosen recipe.

## Not verified (pending owner verification)

- No GUI launch of either artifact (forbidden in this session).
  First startup, platform-plugin selection (xcb vs wayland), and
  translation loading need owner/hardware confirmation.
- No full-application bundle: the probes are representative, not
  the 352-pin P02 closure. Full-closure plugin/import surprises
  (torch, tokenizers, sidecar discovery paths) belong to P05's
  complete-bundle assembly, which must re-run the warn-file gate
  and the dir-search data checks at full scale.
- No target-baseline (Ubuntu 24.04, NVIDIA driver matrix) check.
- Bounded next step on any failure above: file against P05
  ("Assemble the complete Linux application directory bundle",
  issue #2107) with the failing check output — not a
  working-installer claim. No new issue is filed from this
  experiment itself: both candidates built, one is selected, and
  the residual risks already have an owning issue (P05 for
  assembly, owner verification for hardware).

## Unresolved facts

- Exact full-application directory size (probes measure tooling
  overhead shape, not the torch/services closure).
- Whether the Ubuntu 24.04 baseline carries every XCB library
  `libqxcb.so` resolves on this workstation.
- Nuitka 2.6.8-vs-4.x behavior differences are moot (rejected
  path) and were not investigated.

## Appendix: probe sources (reproduce the experiment)

`probe_src/p04_qt_probe.py`:

```python
from __future__ import annotations

import sys
from importlib import resources

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication, QLabel

from p04_runtime_double import RUNTIME_MANIFEST, discover_sidecar


def load_bundled_text(name: str) -> str:
    data_dir = resources.files("probe_data")
    return (data_dir / name).read_text(encoding="utf-8")


def main() -> int:
    app = QApplication(sys.argv)
    translator = QTranslator()
    _ = translator
    plugin_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    label = QLabel(f"plugins={plugin_path} runtime={RUNTIME_MANIFEST['name']}")
    _ = label
    _ = discover_sidecar()
    _ = load_bundled_text("sample.qss")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`probe_src/p04_runtime_double.py`:

```python
from __future__ import annotations

from pathlib import Path

RUNTIME_MANIFEST = {
    "name": "p04-llama-sidecar-double",
    "kind": "native-runtime-double",
    "version": "0.0.0-p04",
    "sha256": "0" * 64,
    "entry": "bin/p04-sidecar-double",
}


def discover_sidecar(root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent
    return base / RUNTIME_MANIFEST["entry"]
```

`probe_src/p04_headless_probe.py`:

```python
from __future__ import annotations

from p04_runtime_double import RUNTIME_MANIFEST, discover_sidecar


def main() -> int:
    print(f"runtime={RUNTIME_MANIFEST['name']} path={discover_sidecar()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`probe_src/probe_data/__init__.py`: one comment line (package
marker). `probe_src/probe_data/sample.qss`:

```
QLabel { color: #e8e8e8; background-color: #1a1a1a; }
```

Environment setup to reproduce:

```bash
uv venv .venv --seed --python 3.13
.venv/bin/pip install pyinstaller==6.12.0 'PySide6==6.9.0'
.venv/bin/pip install nuitka patchelf ordered-set zstandard tomlkit
```
