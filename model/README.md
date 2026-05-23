# model

Top-level root for the AIRunner inference and runtime contract package.

Current scope:

- runtime modality enums and descriptors
- transport-neutral invocation request and response models
- the lowest-level runtime contract surface that can be shared by API and
  service code without importing GUI code

Current limitations:

- this is only the first extraction slice
- runtime registry, sidecar clients, and model managers still mostly live
  under `services/`

See `docs/architecture/layered_product_architecture.md` for the target
package map and `docs/architecture/api_model_extraction_plan.md` for the
current extraction sequence.