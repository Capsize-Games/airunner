# Service Whisper model identity

The service's speech-to-text model identity comes from
[`ModelRegistry`](../../../services/src/airunner_services/model_management/model_registry.py),
not from the generic `AIRUNNER_DEFAULT_STT_HF_PATH` value in the vendored
`airunner-common` settings module. The registered service backend is
`whisper.cpp` with GGML format and pins `ggerganov/whisper.cpp`,
`ggml-large-v3.bin`, revision `c521a4b02f422512d734391fdf08bb08c0862f68`,
SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`,
and size 3,095,033,483 bytes.

[`database/bootstrap/whisper.py`](../../../services/src/airunner_services/database/bootstrap/whisper.py)
reads the registry identity and rejects incompatible explicit repository or
filename overrides before download. The generic setting remains in the
vendored package for other consumers; its historical documentation does not
select the service's whisper.cpp artifact. The model identity record does not
establish the model's license or inference acceptance.

The vendored `airunner-common==6.1.8` `settings.py` file is preserved byte for
byte from the selected wheel. Its wheel SHA-256 is
`ac2110ecbcd965c9a773405494bcecb3d1c6c5f127d22fde81d37478b94088fd`; the
member hash and size are verified against the wheel's `RECORD` and the
corresponding values in `debian/vendor/airunner-common.json`.
