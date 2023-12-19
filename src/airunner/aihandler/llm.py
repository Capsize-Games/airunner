from airunner.aihandler.transformer_runner import TransformerRunner
from airunner.aihandler.logger import Logger as logger


class LLM(TransformerRunner):
    def clear_conversation(self):
        if self.generator.name == "casuallm":
            self.chain.clear()
    
    def do_generate(self, data):
        self.process_data(data)
        self.handle_request()
        self.requested_generator_name = data["request_data"]["generator_name"]
        prompt = data["request_data"]["prompt"]
        model_path = data["request_data"]["model_path"]
        self.generate(
            app=self.app,
            endpoint=data["request_data"]["generator_name"],
            prompt=prompt, 
            model=model_path,
            stream=data["request_data"]["stream"],
            images=[data["request_data"]["image"]],
        )

    def generate(self, **kwargs):
        if self.generator.name == "casuallm":
            prompt = kwargs.get("prompt", "")
            logger.info(f"LLM requested with prompt {prompt}")
            return self.chain.run(prompt)
        elif self.generator.name == "visualqa":
            inputs = self.processor(
                self.image, 
                self.prompt, 
                return_tensors="pt"
            ).to("cuda")
            out = self.model.generate(
                **inputs,
                **kwargs,
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
            logger.error(f"Failed to call generator for {self.generator.name}")
        # self.llm_api.request(**kwargs)
