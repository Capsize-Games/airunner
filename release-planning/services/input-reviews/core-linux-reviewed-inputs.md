# CORE exact-pin review evidence

This record covers the seven exact pins with source-level evidence found for
the current Linux CORE lock. Its scope is limited to the cited artifacts and
build paths; it is not a blanket approval for later versions.

| Distribution | Exact version | Source identity | Artifact evidence | Current policy state |
|---|---:|---|---|---|
| airunner-common | 6.1.8 | `733b0f4c8fb38952866e9cf7be2cc69793a46e92` | Release wheel `ac2110ecbcd965c9a773405494bcecb3d1c6c5f127d22fde81d37478b94088fd`; RECORD and vendored module hashes verified | Owner source |
| python-dotenv | 1.2.2 | `36004e0e34be7665ff2b11a8a4005144f76f176d` | Wheel `1d8214789a24de455a8b8bd8ae6fe3c6b69a5e3d64aa8a8e5d68e694bbcb285a`; RECORD inspected | Exact-pin owner exception recorded |
| pyinstaller | 6.12.0 | `31dbe9ff477716e4790aa317bc9da68766d20659` | Source archive `1834797be48ce1b26015af68bdeb3c61a6c7500136f04e0fc65e468115dec777`; setup path, license, matching Linux hooks, and relevant advisory inspected | Owner exception pending |
| pyinstaller-hooks-contrib | 2026.9 | `222e37fea0d8300595af3601a4f42d2fcf634a37` | Source archive `2748767901acb5cecd1304652b6c7add5bffcff1d71d01207fe24a5d42942a56`; matched CORE hooks and license inspected; PyPI vulnerability metadata was empty | Owner exception pending |
| setuptools | 84.2.1 | `3895f9829fc0e51882981773a823a658eb1d1636` | Wheel `ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2`; RECORD and active PEP 517 build path reviewed | Origin review not recorded |
| wheel | 0.48.0 | `21c4da4c54c3b354cc22dc7f6f6374ffcd560e84` | Wheel `3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab`; RECORD reviewed | Origin review not recorded |
| packaging | 26.3 | `929fd4b1410ac7ef61ef3f45b2f5d7e87711a9b5` | Wheel `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c`; RECORD reviewed | Origin review not recorded |

For setuptools, wheel, and packaging, the source and artifact review evidence
uses official PyPI metadata and cached wheel contents. The raw wheel archives
were not present for independent rehashing in that review; metadata digests
matched the cache records and extracted files passed RECORD checks. The
setuptools review is limited to the active build path and its expected
`distutils-precedence.pth` behavior. The hooks review covers the matched CORE
hook set, not every hook in that project. The PyInstaller advisory review is
scoped to the configured `onedir` mode.

The readiness inventory keeps source review and origin-policy state separate.
The other 44 locked distributions still need exact-version source, build and
install hook, license, advisory, origin, and bundled-instruction review before
the graph can be activated. The three build tools above also need origin
review. The two freeze tools need their existing source-origin exceptions
recorded. No package installation or freeze is authorized by this record.
