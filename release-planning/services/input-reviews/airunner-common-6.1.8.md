# `airunner-common` 6.1.8 release input review

## Reviewed input

- Distribution: `airunner-common==6.1.8` from `Capsize-Games/airunner-common`.
- Source revision: `733b0f4c8fb38952866e9cf7be2cc69793a46e92`.
- Source tree: `4eaea94b4d7991967062640540f4e058678d0b55`.
- Source archive SHA-256: `b1a7783f87f24fe1b429b0795604eb6f968920ca348e569f21dac66ad06c561d`.
- Built wheel: `airunner_common-6.1.8-py3-none-any.whl`, SHA-256 `ac2110ecbcd965c9a773405494bcecb3d1c6c5f127d22fde81d37478b94088fd`.
- The source and wheel carry the GPL-3.0-only license. The license file in the wheel matches the source license bytes.

## Review scope and build evidence

The review covered the pinned source tree, package metadata, build configuration, package modules, bundled files, and the produced wheel. The wheel's 18 `RECORD` entries pass SHA-256 and size checks. Its metadata identifies version 6.1.8, Python `>=3.13.3`, and the base requirement `python-dotenv==1.2.2`. `facehuggershield==1.0.0` appears only in the `legacy-shield` optional extra; it is not a base requirement.

The wheel build used `setuptools==84.2.1` (MIT), `wheel==0.48.0` (MIT), and `packaging==26.3` (Apache-2.0 OR BSD-2-Clause). Their official wheel hashes and primary `RECORD` entries were verified before the isolated build. The build ran from the exact source archive in a network-disabled sandbox using the pre-reviewed tools. No runtime dependencies were installed, and no package modules were imported or executed.

The `python-dotenv==1.2.2` dependency was separately reviewed at its exact source commit and wheel hash. Its wheel SHA-256 is `1d8214789a24de455a8b8bd8ae6fe3c6b69a5e3d64aa8a8e5d68e694bbcb285a`; it has no mandatory runtime dependencies. This record refers only to that reviewed version and artifact.

## Disposition and exclusions

This exact `airunner-common==6.1.8` source input is approved for the reviewed Linux release profile. The review does not establish runtime behavior, dependency resolution, support on other platforms, or release readiness. The active Linux release lock remains `generation_pending` until a complete reproducible dependency resolution is available and validated. FacehuggerShield and the TTS vendor input remain excluded and quarantined.

No application services, models, production data, deployment, or publication were started or used for this review. No sdist was built and no runtime package was installed.
