from airunner.settings import AIRUNNER_ART_ENABLED


art_pipline_data = [
    {
        "pipeline_action": "txt2img",
        "version": "Flux.1 S",
        "category": "flux",
        "classname": "transformers.AutoFeatureExtractor",
        "default": False,
    },
]

llm_pipeline_data = [
    {
        "pipeline_action": "causallm",
        "version": "1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False,
    },
    {
        "pipeline_action": "causallm",
        "version": "0.1",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False,
    },
    {
        "pipeline_action": "causallm",
        "version": "2",
        "category": "llm",
        "classname": "transformers.AutoModelForCausalLM",
        "default": False,
    },
]

if AIRUNNER_ART_ENABLED:
    pipeline_bootstrap_data = art_pipline_data + llm_pipeline_data
else:
    pipeline_bootstrap_data = llm_pipeline_data
