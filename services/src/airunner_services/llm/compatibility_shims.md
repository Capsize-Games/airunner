# LLM Compatibility Shims

The `services/src/airunner_services/llm` package still preserves several
legacy module paths. Those shims are intentional, but they should stay
small and explicit.

## Package-level owners

Prefer these package-level import surfaces for new code:

- `airunner_services.llm.managers`
- `airunner_services.llm.config`
- `airunner_services.llm.utils`
- `airunner_services.llm.tools`

Those packages now resolve their exports from the service-owned modules
directly instead of routing through compatibility wrappers first.

## Intentional remaining legacy module paths

The following modules remain as direct compatibility shims because older
imports still target their full module path:

- `airunner_services.llm.managers.llm_model_manager`
- `airunner_services.llm.managers.llm_request`
- `airunner_services.llm.managers.llm_response`
- `airunner_services.llm.managers.llm_settings`
- `airunner_services.llm.managers.quantization_mixin`
- `airunner_services.llm.managers.tool_manager`
- `airunner_services.llm.managers.workflow_manager`
- `airunner_services.llm.managers.agent.rag_mixin`
- `airunner_services.llm.config.provider_access_policy`
- `airunner_services.llm.utils.get_chatbot`
- `airunner_services.llm.utils.gpt_oss_parser`
- `airunner_services.llm.utils.language`
- `airunner_services.llm.utils.stream_text`
- `airunner_services.llm.utils.text_preprocessing`
- `airunner_services.llm.utils.thinking_parser`
- `airunner_services.llm.tools.web_tools`

These shims should stay as explicit re-export modules. Do not add new
`sys.modules[__name__]` alias wrappers.

## Rule for future cleanup

When compatibility is only needed for package-level imports, prefer
package `__getattr__` exports. Only keep a module-level shim when a
legacy dotted module path must continue to import successfully.