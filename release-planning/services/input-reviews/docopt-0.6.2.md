# `docopt` 0.6.2 input review

## Reviewed input

- Distribution: `docopt==0.6.2`, MIT, from the canonical [`docopt/docopt` repository](https://github.com/docopt/docopt).
- The official upstream release tag `0.6.2` resolves to source commit `944641a7357376a43151bd4a3ca44f9c07c4d1ae`; this was checked with a read-only `git ls-remote` query and resolved independently in the private maintenance copy.
- Sdist SHA-256: `49b3a825280bd66b3aa83585ef59c4a8c82f2c8a522dbe754a8bc8d08c85c491`.
- Built wheel: `docopt-0.6.2-py2.py3-none-any.whl`, SHA-256 `8423591f153f451e5ef653763edd922b9298e06071e0bcdfbc42bec8181a0d06`. The exact reviewed wheel and its MIT license are retained in `package/wheelhouse/`; `package/wheelhouse/docopt-0.6.2.json` records the artifact and license hashes. This is a source-controlled input, not a generated full dependency lock or a claim of active release use.
- The owner’s source-policy exception is limited to this reviewed Python package version and input. It does not extend to `docopt.cpp`, other packages, or different inputs.

## Source and artifact checks

The artifact was built from the exact 0.6.2 sdist and compared against its release tag, not from the later upstream source snapshot `8fea867d4220f1095dae9d6264ec5aa4031fb712`. The 22 sdist files also present in the tagged tree match byte-for-byte. Setuptools adds generated `[egg_info]` defaults to the sdist’s `setup.cfg`; the tagged file contains only the `[wheel]` section. The sdist includes generated `PKG-INFO` and egg-info metadata and omits nine development or CI files. Inspection of the exact release tag confirmed `docopt.py` imports only `sys` and `re`; `setup.py` uses setuptools, imports the package version, reads the README, and defines no custom build or install hook.

The wheel was built with reviewed `setuptools==84.2.1`, `wheel==0.48.0`, and `packaging==26.3` inputs. Their SHA-256 hashes are `ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2`, `3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab`, and `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c`, respectively. Their primary wheel `RECORD` entries were verified before use.

The build ran from the exact sdist with CPython 3.13.5 and uv 0.13.4 in a network-disabled sandbox. The resulting wheel’s five payload `RECORD` entries pass SHA-256 and size checks. Metadata identifies version 0.6.2 and MIT; the wheel includes `LICENSE-MIT`. A temporary offline installation passed an import, version, and one basic argument-parsing smoke check.

## Scope and exclusions

This is evidence for this exact source, wheel, build-tool set, and smoke input. It does not establish the complete service dependency graph, other platforms, or release readiness. The examples and project test suite were not run. No application service, model, GPU, publication, or deployment was used. Detailed private logs and the built wheel are retained in the local ignored audit record.
