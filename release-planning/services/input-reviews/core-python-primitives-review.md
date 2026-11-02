# CORE Python primitives source review

## Exact inputs

All eight versions below match the current CORE constraints, dependency inventory, and captured PyPI JSON records. The release tags and full commits are linked to the corresponding canonical source repositories. PyPI sdist and wheel hashes were checked against the captured release records and the downloaded artifact bytes.

| Package | Role, license, base runtime requirements | Source tag and commit | Sdist SHA-256 | Wheel SHA-256 | Origin-policy status |
| --- | --- | --- | --- | --- | --- |
| [`altgraph==0.17.5`](https://pypi.org/pypi/altgraph/0.17.5/json) | Builder transitive; MIT; none | [v0.17.5](https://github.com/ronaldoussoren/altgraph/tree/v0.17.5), `3719ef2991e982c5d13c8ab76693a41fd8c183a3` | `c87b395dd12fabde9c99573a9749d67da8d29ef9de0125c7f536699b4a9bc9e7` | `f3a22400bce1b0c701683820ac4f3b159cd301acab067c51c653e06961600597` | Covered by owner-approved reviewed-packaging-tools category |
| [`annotated-doc==0.0.5`](https://pypi.org/pypi/annotated-doc/0.0.5/json) | Runtime transitive; MIT; none | [0.0.5](https://github.com/fastapi/annotated-doc/tree/0.0.5), `ef48d6ad51d226f772fd9c5284f55199afe4007c` | `c7e58ce09192557605d8bbd92836d7e1d520ac9580096042c0bfd197efacf1bb` | `117bac03a25ede5df5440e855b32d556049ca169ead221505badf432fed4b101` | Owner origin whitelist recorded |
| [`annotated-types==0.8.0`](https://pypi.org/pypi/annotated-types/0.8.0/json) | Runtime transitive; MIT; none | [v0.8.0](https://github.com/annotated-types/annotated-types/tree/v0.8.0), `9eb96680138269811a39d838d720abc3dce33954` | `13b2beaad985e05e2d6407ee4c4f35590b11f8d693a258a561055cac8f64cab7` | `f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0` | Owner origin whitelist recorded |
| [`typing-extensions==4.16.0`](https://pypi.org/pypi/typing-extensions/4.16.0/json) | Runtime transitive; PSF-2.0; none | [4.16.0](https://github.com/python/typing_extensions/tree/4.16.0), `f29cd28d8ed7642cafb1d18daf5aa41be6a5c0aa` | `dc983d19a509c94dba722ee6abd33940f7c05a89e243c47e907eb4db6f1a43e5` | `481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8` | Owner origin whitelist recorded |
| [`typing-inspection==0.4.4`](https://pypi.org/pypi/typing-inspection/0.4.4/json) | Runtime transitive; MIT; `typing-extensions>=4.15.0` | [v0.4.4](https://github.com/pydantic/typing-inspection/tree/v0.4.4), `83d4dbb74fc367db4403c76be8c0f83cd4b63fbe` | `547274fa6b0a561ccf549cc9524b999a578e737d015d8709d021f9d0d13bea47` | `65b8397ba37ccbce054456aaccddfc91e6e3083c92824df348d96ca832f3f147` | Owner origin whitelist recorded |
| [`idna==3.20`](https://pypi.org/pypi/idna/3.20/json) | Runtime transitive; BSD-3-Clause; no base requirements (development tools are in the `all` extra) | [v3.20](https://github.com/kjd/idna/tree/v3.20), `d55e65e1a3b1ede7f556bc202738066f5597e249` | `a7db850025b95ded1eae8a46181a1a6c56c92c96f0e2b005d9ff8dc0210cab44` | `ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c` | Reviewed; no concrete origin flag observed |
| [`defusedxml==0.7.1`](https://pypi.org/pypi/defusedxml/0.7.1/json) | Runtime transitive; PSFL; none | [v0.7.1](https://github.com/tiran/defusedxml/tree/v0.7.1), `ebff1b493751e2f0775314bdd4188d64f07ea184` | `1bb3032db185915b62d7c6209c5a8792be6a32ab2fedacc84e01b52c51aa3e69` | `a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61` | Owner origin whitelist recorded |
| [`python-dateutil==4.0.0`](https://pypi.org/pypi/python-dateutil/4.0.0/json) | Runtime transitive; BSD-3-Clause; `tzdata` | [4.0.0](https://github.com/dateutil/dateutil/tree/4.0.0), `a78cbd81d5d03b5f126eb36edb92bca78972c804` | `d7295ff14fdc0f92f662100bfb6c551d160ca090f2939f1ec5b9794265c03f06` | `a5e246f79eb80475e691bf93862cead98decd8a498cf53ba0516fcdc0f50dc1c` | Reviewed; no concrete origin flag observed |

## Artifact and source checks

All eight sdists were inspected as archives before extraction. Their members were regular files or directories under the expected package root; no unsafe paths or special entries were found. Each sdist’s overlapping release-tag files were compared byte-for-byte with the tagged source. No runtime Python source file differed. Differences were limited to sdist-generated or normalized packaging metadata, version files, and line endings:

- `altgraph`: 32 files matched; `setup.cfg` was reformatted and given generated egg-info defaults.
- `annotated-doc`: 15 files matched; PDM normalized `pyproject.toml` and inserted release version `0.0.5` into the sdist metadata.
- `annotated-types`: 17 files matched; no tracked source differences.
- `typing-extensions`: 8 files matched; no tracked source differences.
- `typing-inspection`: 31 files matched; only `uv.lock`’s project version changed from `0.4.2` to `0.4.4` in the sdist.
- `idna`: 30 files matched; no tracked source differences.
- `defusedxml`: 48 files matched; `setup.cfg` received generated egg-info defaults.
- `python-dateutil`: 77 files matched; `NEWS` and `docs/make.bat` have line-ending changes, and `_version.py` is generated for the sdist.

Every downloaded wheel matched its PyPI-recorded SHA-256. All wheel `RECORD` payload hashes and sizes passed validation: 12, 7, 6, 4, 8, 15, 15, and 25 entries respectively in the order shown above. Every `.py` file in each wheel matched the corresponding source-distribution file exactly. The licenses in the wheel metadata and included license files agree with the source metadata.

## Packaging and behavior review

The source declares these build paths: setuptools-based `setup.py` for `altgraph` and `defusedxml`; `pdm-backend` for `annotated-doc`; Hatchling for `annotated-types` and `typing-inspection`; Flit Core for `typing-extensions` and `idna`; and Hatchling with `hatch-vcs` plus a README metadata hook for `python-dateutil`. Project build declarations and custom commands were inspected statically. The backend packages themselves were not inspected or installed in this batch, and no build ran.

Notable source behavior is limited to documented API or test/build paths. `altgraph` has an optional Graphviz display/export API that calls configured Graphviz programs through `os.system`; its setup code also defines an `eval()`-based environment-marker parser and notes that hostile configuration would be unsafe. The pinned configuration contains only static metadata and no marker-valued requirements. `defusedxml` has a custom test command that launches its test script, plus network proof-of-concept examples in the sdist; the examples are absent from the wheel. `python-dateutil` has a test utility that downloads timezone data, while its runtime timezone lookup reads resources from the `tzdata` package. `typing-extensions` evaluates annotations only through its explicit evaluation APIs, and `typing-inspection` generates fixed type-check helper functions from source constants.

No telemetry or credential reads were found in the reviewed runtime modules. The source review did not execute any code. In the `python-dateutil` source tag, `AGENTS.md` is excluded from the sdist by the build configuration; it was read as untrusted source data. The upstream CI workflows remain disabled in the private source copies and were not run.

The captured PyPI JSON records had empty vulnerability arrays. An exact-version OSV batch lookup on 2026-11-01 also returned no records for these eight inputs. These database results are limited snapshots, not proof that no vulnerability exists.

## Origin disposition and limits

Static profile review found concrete origin-policy flags for six packages: `altgraph`, `annotated-doc`, `annotated-types`, `typing-extensions`, `typing-inspection`, and `defusedxml`. The existing owner-approved reviewed-packaging-tools category covers `altgraph==0.17.5`. The owner subsequently accepted all reviewed dependency origin flags for this project on 2026-11-01, including the other five exact inputs. `idna` and `python-dateutil` had no concrete flag in the project author/maintainer metadata and primary profiles checked; this does not assert a country of origin.

Separate private maintenance repositories were created for all eight upstream sources. Each is owner-controlled, private, has GitHub Actions disabled, and retains the source history and pinned release tag. Per-package private evidence retains the exact PyPI JSON, sdist, wheel, source comparison, and profile/advisory findings.

No package was installed, imported, built, tested, activated, or used in a bundle. No upstream workflow or package hook ran. This record does not change the shared dependency inventory or readiness status and does not establish CORE release readiness.
