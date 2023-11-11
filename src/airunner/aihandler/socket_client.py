import socket
import json
import threading
import queue
import time


class Response:
    def __init__(self):
        self.images = []
        self.request_type = ""
        self.tile_type = ""


class Options:
    def __init__(self):
        self.prompt = ""
        self.negative_prompt = ""
        self.steps = 15
        self.ddim_eta = 0.1
        self.n_iter = 1
        self.samples = 1
        self.scale = 7.5
        self.seed = 0
        self.model = ""
        self.scheduler = "Euler a"
        self.model_path = ""
        self.model_branch = "main"
        self.width = 768
        self.height = 512
        self.do_nsfw_filter = False
        self.pos_x = 0
        self.pos_y = 0
        self.outpaint_box_rect = [0, 0, 0, 0]
        self.hf_token = ""
        self.model_base_path = "/home/joe/stablediffusion"
        self.use_last_channels = True
        self.use_enable_sequential_cpu_offload = False
        self.enable_model_cpu_offload = False
        self.use_attention_slicing = False
        self.use_tf32 = False
        self.use_cudnn_benchmark = False
        self.use_enable_vae_slicing = True
        self.use_accelerated_transformers = True
        self.use_torch_compile = False
        self.use_tiled_vae = True


class ClientData:
    def __init__(self):
        self.action = "txt2img"
        self.options = Options()
        self.request_type = ""
        self.tile_type = ""


class SocketClient:
    def __init__(self):
        self.socket = None
        self.base64image = None
        self.worldMapGenerator = None
        self._prompt = ""
        self._negative_prompt = ""
        self._serverResponseQueue = queue.Queue()
        self.request_queue = queue.Queue()
        self.world_generated = False

    @property
    def Data(self):
        options = Options()
        options.prompt = self._prompt
        options.negative_prompt = self._negative_prompt
        data = ClientData()
        data.options = options
        return data

    def start(self):
        self.connect()

    def is_connected(self):
        if self.socket is None:
            return False
        else:
            return True

    def update(self):
        if self.is_connected():
            prompt = input("Enter a prompt: ")
            self.do_request(prompt, "")
            if not self.world_generated:
                self.world_generated = True
            if not self._serverResponseQueue.empty():
                response = self._serverResponseQueue.get()
                self.response_handler(response)
            if not self.request_queue.empty():
                request = self.request_queue.get()
                self.do_socket_request(request)
        else:
            self.close()

    def handle_response(self):
        bytesReceived = 0
        response = ""
        endMessage = bytearray(1024)
        self.socket.settimeout(0.1)
        while self.socket is not None and self.is_connected():
            try:
                responseBytes = self.socket.recv(1024)
                response += responseBytes.decode('utf-8')
                bytesReceived += len(responseBytes)
                if len(responseBytes) == 1024 and responseBytes == endMessage:
                    self._serverResponseQueue.put(response)
                    bytesReceived = 0
                    response = ""
            except socket.error as e:
                pass

    def response_handler(self, response):
        # res = json.loads(response, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
        # print(res.request_type)
        # # convert res.images[0] base64 to PIL image and save
        # base64image = res.images[0]
        # image = Image.open(base64image)
        # image.save("test.png")
        pass

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(("127.0.0.1", 5000))
            threading.Thread(target=self.handle_response).start()
        except socket.error as e:
            self.socket = None
        if self.socket is None:
            threading.Timer(1, self.connect).start()

    def do_request(self, prompt, negativePrompt, seed=42, requestType="", tileType=""):
        model = ""
        prefix = ""
        trigger = ""
        d = {
            "action": "txt2img",
            "options": {
                "prompt": "",
                "negative_prompt": "",
                "steps": 15,
                "ddim_eta": 0.1,
                "n_iter": 1,
                "samples": 1,
                "scale": 7.5,
                "seed": 0,
                "model": "",
                "scheduler": "Euler a",
                "model_path": "",
                "model_branch": "main",
                "width": 512,
                "height": 512,
                "do_nsfw_filter": False,
                "pos_x": 0,
                "pos_y": 0,
                "outpaint_box_rect": [0, 0, 0, 0],
                "hf_token": "",
                "model_base_path": "/home/joe/stablediffusion",
                "use_last_channels": True,
                "use_enable_sequential_cpu_offload": False,
                "enable_model_cpu_offload": False,
                "use_attention_slicing": False,
                "use_tf32": False,
                "use_cudnn_benchmark": False,
                "use_enable_vae_slicing": True,
                "use_accelerated_transformers": True,
                "use_torch_compile": False,
                "use_tiled_vae": True
            },
            "request_type": "",
            "tile_type": ""
        }
        if requestType == "scene":
            model = "PublicPrompts/All-In-One-Pixel-Model"
            prefix = "16bitscene"
            trigger = ""
        elif requestType == "character":
            model = "PublicPrompts/All-In-One-Pixel-Model"
            prefix = "pixelart profile picture of"
            trigger = "pixelsprite style"
        elif requestType == "world_map_tile":
            model = "PublicPrompts/All-In-One-Pixel-Model"
            prefix = "isometric"
            trigger = "isopixel style"
        prompt = prefix + " " + prompt + " " + trigger
        self._prompt = prompt
        self._negative_prompt = negativePrompt
        d["options"]["prompt"] = prompt
        d["options"]["negative_prompt"] = negativePrompt
        d["options"]["model_path"] = "PublicPrompts/All-In-One-Pixel-Model"
        d["options"]["model"] = "PublicPrompts/All-In-One-Pixel-Model"
        d["options"]["seed"] = seed
        print("enqueue " + json.dumps(d))
        self.request_queue.put(json.dumps(d))

    def do_socket_request(self, message):
        print("sending message: " + message + "")
        try:
            messageBytes = message.encode('utf-8')
            i = 0
            while i < len(messageBytes):
                packetBytes = messageBytes[i:i+1024]
                self.socket.send(packetBytes)
                i += 1024
            self.send_end_message()
        except socket.error as e:
            print("Socket exception: " + str(e))
            self.request_queue.put(message)

    def send_end_message(self):
        endMessage = bytearray(1024)
        self.socket.send(endMessage)

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
            self.connect()

    def on_application_quit(self):
        self.close()


if __name__ == "__main__":
    socketClient = SocketClient()
    socketClient.start()
    while True:
        socketClient.update()
        time.sleep(0.1)
