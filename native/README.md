# native

Top-level root for native launcher, bundle, and installer assets.

Current status:

- this is the real importable home of the native bootstrap package
- it currently packages the physical `shared`, `services`, `gui`, and
	`native` package roots
- the target steady state is for `native` to package `model`, `api`,
	`services`, and optionally `gui`
- no service orchestration or GUI behavior should move here

This directory now owns the launcher and runtime-sidecar build inputs, and the
importable native-owned Python bootstrap package now lives in
`native/src/airunner_native/`.

The canonical target architecture lives in
`docs/architecture/layered_product_architecture.md`.

Canonical native package metadata now lives in `native/setup.py`.

Checkout imports now resolve from `native/src/airunner_native/` directly via
the repo bootstrap path configuration.

Some current monorepo bootstrap and packaging flows still compose package
roots through repo-local path wiring and `shared` installs. Treat that as
transitional migration debt rather than the steady-state native package model.

The native package owns the launcher entry point and bundle assembly. The
desktop GUI is one optional packaged dependency of that launcher surface
rather than a hard requirement for every install.

Default repo-local native validation:

- `airunner-tests --package native`
- `pytest native/src -m "not benchmark and not integration"`

Pair this with focused launcher or packaging smoke checks when a change touches
bundle assembly, installer scripts, or launcher startup behavior. The broader
package matrix and shim retirement plan live in
`docs/architecture/package_split_contract.md`.