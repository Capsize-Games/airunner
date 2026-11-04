# Compel 2.4.0+capsize.1 input review

## Source and metadata change

- Distribution: `compel==2.4.0+capsize.1`, based on upstream tag `v2.4.0`, commit `c60b9fbc7fa9eb443af96c326951589b5ca7a299`.
- Canonical upstream source: [damian0815/compel](https://github.com/damian0815/compel). The v2.4.0 sdist SHA-256 is `9d935d35bb4d16fa21d4b3b529d8b8f9dc784d67b44e42f46cd48c9dd321adc2`.
- The metadata-only patch changes the distribution version to `2.4.0+capsize.1` and moves `notebook>=6.5.7` from required runtime dependencies to an optional `notebook` extra. The MIT license and all runtime source files are unchanged.
- Upstream issue [#133](https://github.com/damian0815/compel/issues/133) reports the observed metadata mismatch and asks whether Notebook should be optional.

## Review findings

The exact v2.4.0 source was read as data. `notebook` references are confined to demos/examples; no runtime module imports Jupyter or notebook APIs. The runtime package's remaining declared requirements are diffusers, pyparsing, torch, and transformers. Build metadata uses standard `setuptools.build_meta`; there is no custom `setup.py` or project-specific build/install hook. No unexpected network, socket, subprocess, telemetry, credential access, or agent instruction was found in the reviewed runtime/build scope. The upstream MIT `LICENSE` is retained byte-for-byte as `package/wheelhouse/compel-LICENSE`.

The upstream history and exact metadata patch are retained in an owner-controlled private maintenance copy with GitHub Actions disabled and no upstream synchronization. The patch changes only `pyproject.toml`; its commit is `166fded6c7ec3b54e704cf81e90607540443051e`.

## Wheel and build evidence

- Built wheel: `compel-2.4.0+capsize.1-py3-none-any.whl`, SHA-256 `4ab7bb76510acdd9e607e1f2202cbcb18adbe2750ed26b1fa406e4cc91cb6e43`, size 37,088 bytes. `package/wheelhouse/compel-2.4.0+capsize.1.json` records its provenance and hashes.
- Built from the exact patched source with CPython 3.13.5 and uv 0.13.4 in a network-disabled sandbox. The isolated environment contained only `setuptools==84.2.1`, `wheel==0.48.0`, and `packaging==26.3`; their wheel hashes are in the artifact manifest and were checked before installation into the build environment.
- The wheel's `RECORD` hashes and sizes validate. Wheel metadata has the exact local version, retains the four non-Notebook runtime requirements, and places Notebook only in the optional extra. The eight runtime Python source modules compare byte-for-byte with the upstream source. The wheel includes the MIT license text.
- No Compel package, runtime dependency, or torch was installed or imported. No application, model, GPU, or runtime behavior was exercised.

## Scope and limits

This review concerns the exact upstream source, metadata-only patch, tool inputs, and built wheel recorded above. It does not review other Compel versions or establish runtime/model behavior. The private copy is maintained separately from upstream; this review does not imply an upstream patch has been accepted.
