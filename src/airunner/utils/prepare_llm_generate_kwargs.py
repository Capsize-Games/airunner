def prepare_llm_generate_kwargs(settings):
    data = settings["generator_settings"]

    min_val = 0.0001

    length_penalty = data["length_penalty"] / 1000
    repetition_penalty = data["repetition_penalty"] / 100
    top_p = data["top_p"] / 1000
    temperature = data["temperature"] / 10000

    if length_penalty < min_val:
        length_penalty = min_val

    if repetition_penalty < min_val:
        repetition_penalty = min_val

    if top_p < min_val:
        top_p = min_val

    if temperature < min_val:
        temperature = min_val
    
    return dict(
        length_penalty=length_penalty,
        repetition_penalty=repetition_penalty,
        do_sample=data["do_sample"],
        early_stopping=data["early_stopping"],
        eta_cutoff=data["eta_cutoff"],
        max_new_tokens=data["max_new_tokens"],
        min_length=data["min_length"],
        no_repeat_ngram_size=data["ngram_size"],
        num_return_sequences=1,
        temperature=temperature,
        top_k=data["top_k"],
        top_p=top_p,
        use_cache=data["use_cache"],
        num_beams=data["num_beams"],
    )
