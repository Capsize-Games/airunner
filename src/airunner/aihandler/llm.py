from airunner.aihandler.transformer_runner import TransformerRunner
from airunner.aihandler.logger import Logger as logger


class LLM(TransformerRunner):
    def clear_conversation(self):
        if self.generator.name == "casuallm":
            self.chain.clear()

    def generate(self, **kwargs):
        if self.generator.name == "casuallm":
            return self.chain.run(kwargs.get("prompt", ""))
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
                print("DECODING RESULT")
                answer = self.processor.decode(
                    res,
                    skip_special_tokens=True
                )
                answers.append(answer.strip().lower())
            return answers
        else:
            logger.error(f"Failed to call generator for {self.generator.name}")
