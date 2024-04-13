def parse_template(template: dict) -> str:
    system_instructions = template["system_instructions"]
    model = template["model"]
    llm_category = template["llm_category"]
    template = template["template"]
    parsed_template = ""
    if llm_category == "casuallm":
        if model in [
            "mistralai/Mistral-7B-Instruct-v0.1",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ]:
            parsed_template = "\n".join((
                "[INST]<<SYS>>",
                system_instructions,
                "<</SYS>>",
                template,
                "[/INST]"
            ))
    return parsed_template
