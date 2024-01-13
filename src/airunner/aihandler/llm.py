import torch
import traceback

from airunner.aihandler.transformer_runner import TransformerRunner
from airunner.aihandler.logger import Logger
from airunner.aihandler.enums import MessageCode
import os
from jinja2 import Environment, FileSystemLoader

from transformers.pipelines.conversational import Conversation


class LLM(TransformerRunner):
    def clear_conversation(self):
        if self.requested_generator_name == "casuallm":
            self.chain.clear()
    
    def do_generate(self, data):
        Logger.info("Generating with LLM")
        self.process_data(data)
        self.handle_request()
        self.requested_generator_name = data["request_data"]["generator_name"]
        prompt = data["request_data"]["prompt"]
        model_path = data["request_data"]["model_path"]
        return self.generate(
            # app=self.app,
            # endpoint=data["request_data"]["generator_name"],
            # prompt=prompt, 
            # model=model_path,
            # stream=data["request_data"]["stream"],
            # images=[data["request_data"]["image"]],
        )
    
    history = []

    def generate(self):
        Logger.info("Generating with LLM " + self.requested_generator_name)
        # Create a FileSystemLoader object with the directory of the template
        HERE = os.path.dirname(os.path.abspath(__file__))
        file_loader = FileSystemLoader(os.path.join(HERE, "chat_templates"))

        # Create an Environment object with the FileSystemLoader object
        env = Environment(loader=file_loader)

        # Load the template
        # Load the template
        chat_template = self.prompt_template#env.get_template('chat.j2')

        prompt = self.prompt
        if prompt is None or prompt == "":
            traceback.print_stack()
            return
        
        if self.requested_generator_name == "casuallm":
            history = []
            for message in self.history:
                if message["role"] == "user":
                    #history.append("[INST]" + self.username + ': "'+ message["content"] +'"[/INST]')
                    history.append(self.username + ': "'+ message["content"])
                else:
                    history.append(self.botname + ': "'+ message["content"] +'"')
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
                #"botmood": "angry. He hates " + self.username
                #"botmood": "happy. He loves " + self.username
                #"botmood": "Sad. He is very depressed"
                #"botmood": "Tired. He is very sleepy"
            }

            self.history.append({
                "role": "user",
                "content": prompt
            })

            # Render the template with the variables
            #rendered_template = chat_template.render(variables)

            # iterate over variables and replace again, this allows us to use variables
            # in custom template variables (for example variables inside of botmood and bot_personality)
            rendered_template = chat_template
            for n in range(2):
                for key, value in variables.items():
                    print("RENDERING", key, value)
                    rendered_template = rendered_template.replace("{{ " + key + " }}", value)

            print("x"*80)
            print("RENDERED TEMPLATE:")
            print(rendered_template)

            # Encode the rendered template
            encoded = self.tokenizer.encode(rendered_template, return_tensors="pt")
            print("RENDERED TEMPLATE", rendered_template)

            model_inputs = encoded.to("cuda" if torch.cuda.is_available() else "cpu")

            # Generate the response
            Logger.info("Generating...")
            generated_ids = self.model.generate(
                model_inputs,
                min_length=0,
                max_length=1000,
                num_beams=1,
                do_sample=True,
                top_k=20,
                eta_cutoff=10,
                top_p=1.0,
                num_return_sequences=self.sequences,
                eos_token_id=self.tokenizer.eos_token_id,
                early_stopping=True,
                repetition_penalty=1.15,
                temperature=0.7,
            )
            Logger.info("GENERATED")

            # Decode the new tokens
            decoded = self.tokenizer.batch_decode(generated_ids)[0]
            decoded = decoded.replace(self.tokenizer.batch_decode(model_inputs)[0], "")
            decoded = decoded.replace("</s>", "")

            # Extract the actual message content
            start_index = decoded.find('"') + 1
            end_index = decoded.rfind('"')
            decoded = decoded[start_index:end_index]

            # strip BOTNAME: from decoded
            decoded = decoded.replace(self.botname + ": ", "")

            Logger.info("Decoded: " + decoded)
            # remove white space
            decoded = decoded.strip()
            if decoded == "":
                decoded = "ERROR"

            self.history.append({
                "role": "assistant",
                "content": decoded
            })

            # print(self.history)

            # print("*"*80)
            # print(decoded)

            #return decoded
            self.engine.send_message(decoded, code=MessageCode.TEXT_GENERATED)
        elif self.requested_generator_name == "visualqa":
            inputs = self.processor(
                self.image, 
                prompt, 
                return_tensors="pt"
            ).to("cuda")
            out = self.model.generate(
                **inputs
            )

            answers = []
            for res in out:
                answer = self.processor.decode(
                    res,
                    skip_special_tokens=True
                )
                answers.append(answer.strip().lower())
            return answers
        else:
            Logger.error(f"Failed to call generator for {self.requested_generator_name}")
        # self.llm_api.request(**kwargs)
