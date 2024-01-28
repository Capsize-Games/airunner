import threading
from typing import List, Optional, Any

from langchain.llms.huggingface_pipeline import HuggingFacePipeline, VALID_TASKS
from langchain.llms.utils import enforce_stop_tokens
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser, LLMResult, Generation
from langchain_core.callbacks import CallbackManagerForLLMRun
from transformers import pipeline, AutoModelForCausalLM

from airunner.aihandler.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode


class StreamHuggingFacePipeline(HuggingFacePipeline):
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        # Encode the rendered template
        encoded = self.tokenizer(self.render, return_tensors="pt")
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


class LangChainHandler(TokenizerHandler):
    auto_class_ = AutoModelForCausalLM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipe = None
        self.chain = None
        self.prompt_template = None

    def post_load(self):
        self.load_pipeline()
        self.load_prompt_template()
        self.load_chain()

    def load_pipeline(self):
        pipeline_object = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=10
        )
        self.pipe = StreamHuggingFacePipeline(
            pipeline=pipeline_object
        )

    def load_prompt_template(self):
        self.prompt_template = PromptTemplate.from_template(self.template)

    def load_chain(self):
        parser = StrOutputParser()
        self.chain = self.prompt_template | self.pipe | parser

    def do_generate(self):
        self.logger.info("do_generate")


    # async def do_generate_async(self):
    #     async for chunk in self.chain.astream(dict(
    #         input=self.prompt,
    #         username=self.username,
    #         botname=self.botname,
    #         bot_mood=self.bot_mood,
    #         bot_personality=self.bot_personality,
    #     )):
    #         print(chunk)
    #         self.emit(
    #             SignalCode.LLM_TEXT_STREAMED_SIGNAL,
    #             dict(
    #                 message=chunk,
    #                 is_first_message=is_first_message,
    #                 is_end_of_message=is_end_of_message,
    #                 name=self.botname,
    #             )
    #         )
    #         is_first_message = False
    #     self.emit(
    #         SignalCode.LLM_TEXT_STREAMED_SIGNAL,
    #         dict(
    #             message="",
    #             is_first_message=False,
    #             is_end_of_message=True,
    #             name=self.botname,
    #         )
    #     )
