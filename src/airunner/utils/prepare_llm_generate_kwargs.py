def prepare_llm_generate_kwargs(settings):
    min_val = 0.0001
    length_penalty = settings.length_penalty / 1000.0
    repetition_penalty = settings.repetition_penalty / 100.0
    top_p = settings.top_p / 1000.0
    temperature = settings.temperature / 10000.0

    if length_penalty < min_val:
        length_penalty = min_val

    if repetition_penalty < min_val:
        repetition_penalty = min_val

    if top_p < min_val:
        top_p = min_val

    if temperature < min_val:
        temperature = min_val

    return dict(
        # length_penalty=length_penalty,
        # repetition_penalty=repetition_penalty,
        do_sample=settings.do_sample,
        early_stopping=settings.early_stopping,
        eta_cutoff=settings.eta_cutoff,
        max_new_tokens=settings.max_new_tokens,
        min_length=settings.min_length,
        # no_repeat_ngram_size=data["ngram_size"],
        num_return_sequences=1,
        temperature=temperature,
        top_k=settings.top_k,
        top_p=top_p,
        # use_cache=data["use_cache"],
        # num_beams=data["num_beams"],
    )
