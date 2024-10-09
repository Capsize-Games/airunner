def parse_template(template: dict) -> str:
    system_instructions = template["system_instructions"]
    model = template["model"]
    llm_category = template["llm_category"]
    template = template["template"]
    parsed_template = ""
    if llm_category == "causallm":
        if model in [
            "w4ffl35/Mistral-7B-Instruct-v0.3-4bit"
        ]:
            parsed_template = "\n".join((
                "[INST]<<SYS>>",
                system_instructions,
                "<</SYS>>",
                template,
                "[/INST]"
            ))
    return parsed_template
