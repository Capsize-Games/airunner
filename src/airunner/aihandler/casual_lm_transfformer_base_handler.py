import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from airunner.aihandler.transformer_base_handler import TransformerBaseHandler


class CasualLMTransformerBaseHandler(TransformerBaseHandler):
    auto_class_ = AutoModelForCausalLM

    def do_generate(self, prompt, chat_template):
        history = []
        for message in self.history:
            if message["role"] == "user":
                # history.append("<s>[INST]" + self.username + ': "'+ message["content"] +'"[/INST]')
                history.append(self.username + ': "' + message["content"] + '"')
            else:
                # history.append(self.botname + ': "'+ message["content"] +'"</s>')
                history.append(self.botname + ': "' + message["content"])
        history = "\n".join(history)
        if history == "":
            history = None

        # Create a dictionary with the variables
        variables = {
            "username": self.username,
            "botname": self.botname,
            "history": history or "",
            "input": prompt,
            "bos_token": self.tokenizer.bos_token,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }

        self.history.append({
            "role": "user",
            "content": prompt
        })

        # Render the template with the variables
        # rendered_template = chat_template.render(variables)

        # iterate over variables and replace again, this allows us to use variables
        # in custom template variables (for example variables inside of botmood and bot_personality)
        rendered_template = chat_template
        for n in range(2):
            for key, value in variables.items():
                rendered_template = rendered_template.replace("{{ " + key + " }}", value)

        # Encode the rendered template
        encoded = self.tokenizer(rendered_template, return_tensors="pt")
        model_inputs = encoded.to("cuda" if torch.cuda.is_available() else "cpu")

        # Generate the response
        self.logger.info("Generating...")
        import threading
        thread = threading.Thread(target=self.model.generate, kwargs=dict(
            model_inputs,
            min_length=self.min_length,
            max_length=self.max_length,
            num_beams=self.num_beams,
            do_sample=True,
            top_k=self.top_k,
            eta_cutoff=self.eta_cutoff,
            top_p=self.top_p,
            num_return_sequences=self.sequences,
            eos_token_id=self.tokenizer.eos_token_id,
            early_stopping=True,
            repetition_penalty=self.repetition_penalty,
            temperature=self.temperature,
            streamer=self.streamer
        ))
        thread.start()
        # strip all new lines from rendered_template:
        rendered_template = rendered_template.replace("\n", " ")
        rendered_template = "<s>" + rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        for new_text in self.streamer:
            # strip all newlines from new_text
            parsed_new_text = new_text.replace("\n", " ")
            streamed_template += parsed_new_text
            streamed_template = streamed_template.replace("<s> [INST]", "<s>[INST]")
            # iterate over every character in rendered_template and
            # check if we have the same character in streamed_template
            if not replaced:
                for i, char in enumerate(rendered_template):
                    try:
                        if char == streamed_template[i]:
                            skip = False
                        else:
                            skip = True
                            break
                    except IndexError:
                        skip = True
                        break
            if skip:
                continue
            elif not replaced:
                replaced = True
                streamed_template = streamed_template.replace(rendered_template, "")
            else:
                if "</s>" in new_text:
                    streamed_template = streamed_template.replace("</s>", "")
                    new_text = new_text.replace("</s>", "")
                    is_end_of_message = True
                yield dict(
                    message=new_text,
                    is_first_message=is_first_message,
                    is_end_of_message=is_end_of_message,
                    name=self.botname,
                )
                is_first_message = False

            if is_end_of_message:
                self.history.append({
                    "role": "bot",
                    "content": streamed_template.strip()
                })
                streamed_template = ""
                replaced = False

    def load_tokenizer(self, local_files_only=None):
        self.logger.info(f"Loading tokenizer from {self.current_model_path}")
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.current_model_path,
                local_files_only=local_files_only,
                token=self.request_data.get("hf_api_key_read_key"),
                device_map=self.device,
            )
            self.logger.info("Tokenizer loaded")
        except OSError as e:
            if "Checkout your internet connection" in str(e):
                if local_files_only:
                    self.logger.warning(
                        "Unable to load tokenizer, model does not exist locally, trying to load from remote"
                    )
                    return self.load_tokenizer(local_files_only=False)
                else:
                    self.logger.error(e)
        except Exception as e:
            self.logger.error(e)

        if self.tokenizer:
            self.tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")
