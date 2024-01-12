import requests
import json
import base64
from io import BytesIO


class LLMAPI:
    def __init__(self, app):
        self.app = app
        self.port = 11434
        self.uri = "http://localhost"
        self.base_api = "/api/"
        self.url = f"{self.uri}:{self.port}{self.base_api}"
    
    def request(
        self, 
        app,
        endpoint, 
        prompt, 
        model=None,
        images=None, 
        options=None,
        system_message=None, 
        template=None,
        context=None,
        stream=False,
        raw=False
    ):
        model = "stablelm-zephyr"
        if endpoint == "casuallm":
            model = "llama2-uncensored"
            endpoint = "generate"
        elif endpoint == "visualqa":
            model = "bakllava"
            endpoint = "generate"

        json_options = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "raw": raw
        }
        print(json_options)

        if images is not None:
            # convert images from PIL to base64
            base64_images = []
            for image in images:
                if image is None:
                    continue
                image = image.convert("RGB")
                image = self.image_to_base64(image)
                base64_images.append(image)
            json_options["images"] = base64_images
        
        if options is not None:
            json_options["options"] = options
        
        if system_message is not None:
            json_options["system"] = system_message
        
        if template is not None:
            json_options["template"] = template
        
        if context is not None:
            json_options["context"] = context

        with requests.post(f"{self.url}{endpoint}", stream=True, json=json_options) as response:
            try:
                for chunk in response.iter_lines():
                    if chunk:  # filter out keep-alive new chunks
                        chunk = chunk.decode("utf-8")
                        chunk_dict = json.loads(chunk)
                        print(chunk_dict)
                        if "error" in chunk_dict:
                            if "try pulling it first" in chunk_dict["error"]:
                                import os
                                os.system(f"ollama pull {model}")
                                self.request(
                                    app=app,
                                    endpoint=endpoint, 
                                    prompt=prompt, 
                                    model=model,
                                    images=images, 
                                    options=options,
                                    system_message=system_message, 
                                    template=template,
                                    context=context,
                                    stream=stream,
                                    raw=raw
                                )
                                return
                        app.token_signal.emit(chunk_dict["response"])
            except KeyboardInterrupt:
                response.close()
                return
        app.token_signal.emit("[END]")
    
    def image_to_base64(self, image):
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue())
        return img_str.decode('utf-8')