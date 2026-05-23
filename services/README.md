# services

Top-level root for the current AIRunner service orchestration package.

Current status:

- this is the real importable home of the service package
- it currently contains the service orchestration layer plus the embedded API
	and model/runtime implementation that will be split further
- no new GUI widgets, client-local settings, or other GUI-only behavior should
	be added here

Current ownership:

- API routes and server bootstrap
- modality orchestration
- runtime registry and sidecar coordination
- shared persistence and jobs

Target direction:

- `services/` should end at orchestration, persistence, downloads, policy,
	agents, tools, and modality coordination
- the future top-level `api/` package should own server-side wire schemas,
	serialization rules, transport adapters, and API-side request handling
- the future top-level `model/` package should own runtime and inference
	implementation
- consumer layers should own their own clients instead of importing
	`airunner_api`

The importable service-owned code lives in `services/src/airunner_services/`.

Checkout imports now resolve from `services/src/airunner_services/` directly.

The canonical target architecture lives in
`docs/architecture/layered_product_architecture.md`.

Current monorepo bootstrap commands elsewhere in the repo still use
repo-composed `PYTHONPATH` wiring and `shared` installs. That is transitional
migration debt, not the intended steady-state service package model.

Service-owned CLI entry points and the database migration assets now live
under `services/src/airunner_services/bin/` and
`services/src/airunner_services/database/`.

Runtime dependency profiles such as `llm-native`, `art-python`, `tts-python`,
`desktop`, and `windows` are now owned by `services/package_metadata.py`.

Client-local GUI preferences such as the display language, selected
playback and recording devices, and GUI-only `ApplicationSettings`
state do not belong in the shared service database. The service-owned
settings tables now retain only modality and runtime defaults that make
sense for non-GUI clients.

Default repo-local service validation:

- `airunner-tests --package services`
- `pytest services/src -m "not benchmark and not integration"`

When a change touches daemon routes, workers, or runtime orchestration, pair
that package surface with the relevant runtime smoke command documented in
`docs/architecture/package_split_contract.md`.