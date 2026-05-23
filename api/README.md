# api

Top-level root for the AIRunner API contract package.

Current scope:

- transport-neutral envelopes and shared request or response models
- streaming payload formats and serialization rules
- FastAPI and other server-side transport-adapter surfaces
- API-side request handling that stays local to the API layer

Current limitations:

- this is only the first extraction slice
- several transport and wrapper modules are still transitional wrappers
  around service-owned implementations
- consumer-owned client code still needs to be removed from this package
- FastAPI still lives physically under `services/` and remains a transitional
  adapter behind the `airunner_api.transport` surface

See `docs/architecture/layered_product_architecture.md` for the target
package map and `docs/architecture/api_model_extraction_plan.md` for the
current extraction sequence.