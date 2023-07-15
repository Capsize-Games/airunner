import json
import logging
import queue
import threading
import time
import base64
import traceback

from settings import LOG_LEVEL, MessageCode
from io import BytesIO
from PIL import Image
from logger import logger
from runner import SDRunner


class OfflineClient:
    sd_runner = None
    app = None
    current_txt2img_model = None
    current_inpaint_model = None
    response_worker = None
    request_worker = None
    response_worker_thread = None
    request_worker_thread = None
    quit_event = False

    @property
    def message(self):
        """
        Does nothing. Only used for the setter.
        """
        return ""

    @message.setter
    def message(self, msg):
        """
        Set the message property
        """
        if msg == "cancel":
            logger.info("cancel message recieved")
            self.cancel()
        else:
            logger.info("Putting message in queue")
            self.queue.put(msg)

    @property
    def response(self):
        """
        Get the response from the server
        :return: response string
        """
        return ""

    @response.setter
    def response(self, msg):
        """
        Set the response
        :param msg:
        :return: None
        """
        self.res_queue.put(msg)

    def cancel(self):
        self.sd_runner.cancel()

    def __init__(self, **kwargs):
        self.socket_server=kwargs.get("socket_server", None)
        self.queue = queue.Queue()
        self.res_queue = queue.Queue()
        self.logger = logging.getLogger()
        self.do_start()

    def image_handler(self, images, data, nsfw_content_detected):
        logger.info("Image handler called")
        if self.socket_server:
            logger.info("Sending image to socket server")
            # convert image to base64 by using the PIL library and send it to the server
            buffered = BytesIO()

            # scale for pixel art
            image = images[0]
            width = image.width
            height = image.height
            image = image.resize((int(width / 4), int(height / 4)), resample=Image.BICUBIC)
            image = image.quantize(24, kmeans=4)
            image = image.resize((width, height), resample=Image.NEAREST)

            image.save(buffered, format="PNG")

            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            response_type = "scene"
            tile_type = None

            response_type = data["request_type"]
            if response_type == "world_map":
                tile_type = data["tile_type"]

            data = {
                "image": image_base64,
                "type": response_type,
                "tile_type": tile_type
            }
            self.socket_server.send_response(data)
        else:
            # save image to disc
            for index, image in enumerate(images):
                image.save(f"image_{index}.png")

    def error_handler(self, error):
        self.send_message(str(error), MessageCode.ERROR)

    def message_handler(self, message=None, error=False):
        if error:
            traceback.print_exc()
            logger.error(message)
        else:
            logger.info(message)

    def tqdm_callback(self, step, total, action, image=None, data=None):
        if self.socket_server:
            # convert image to base64 by using the PIL library and send it to the server
            if image is not None:
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            else:
                image_base64 = None

            data = {
                "step": step,
                "total": total,
                "action": action,
                "image": image_base64
            }
            self.socket_server.send_response(data)

    def do_start(self):
        # create a stable diffusion runner service
        # sd_runner_thread = self.start_thread(
        #     target=self.init_sd_runner,
        #     name="init stable diffusion runner"
        # )
        # sd_runner_thread.join()
        self.init_sd_runner()
        self.force_request_worker_reset()

    def init_sd_runner(self):
        # save sd_runner to disc and load from it next time
        # this is to avoid the overhead of creating a new sd_runner
        # every time we start the client
        self.sd_runner = SDRunner(
            app=self.app,
            tqdm_callback=self.tqdm_callback,
            message_handler=self.message_handler,
            error_handler=self.error_handler,
            image_handler=self.image_handler
        )

    def handle_response(self, response):
        """
        Handle the response from the server
        :param response:
        :return: None
        """
        res = json.loads(response.decode("utf-8"))
        if "response" in res:
            self.response = response
        else:
            self.message = response

    def handle_error(self, error):
        traceback.print_exc()
        logger.error(error)

    def callback(self, data):
        action = data.get("action")
        model = None
        model = data["options"][f"{data['action']}_model"]
        # on model change, reload the runner
        if (action in ("txt2img", "img2img") and self.current_txt2img_model != model) or (action in ("inpaint", "outpaint") and self.current_inpaint_model != model):
            do_reload = False
            if action in ("txt2img", "img2img"):
                if self.current_txt2img_model is not None:
                    do_reload = True
                self.current_txt2img_model = model
            elif action in ("inpaint", "outpaint"):
                if self.current_inpaint_model is not None:
                    do_reload = True
                self.current_inpaint_model = model
            if do_reload:
                # self.init_sd_runner()
                self.sd_runner.initialized = False
                self.sd_runner.reload_model = True

        if (action in ("txt2img", "img2img") and self.sd_runner.action in ("inpaint", "outpaint")) or \
            (action in ("inpaint", "outpaint") and self.sd_runner.action in ("txt2img", "img2img")):
            self.sd_runner.initialized = False

        self.sd_runner.generator_sample(
            data,
            self.image_handler,
            self.error_handler
        )

    def create_worker_thread(self):
        # start worker in a new thread using the self.worker method
        self.response_worker = ResponseWorker(client=self)
        self.request_worker = RequestWorker(client=self, callback=self.callback)
        # threading for self.response_worker.startWork
        self.response_worker_thread = threading.Thread(target=self.response_worker.startWork)
        self.request_worker_thread = threading.Thread(target=self.request_worker.startWork)
        self.response_worker_thread.daemon = True
        self.request_worker_thread.daemon = True
        self.response_worker_thread.start()
        self.request_worker_thread.start()

    def force_request_worker_reset(self):
        self.force_request_worker_quit()
        self.create_worker_thread()

    def force_request_worker_quit(self):
        if self.request_worker_thread is not None:
            self.request_worker.client.queue.put("quit")
            self.request_worker_thread.join()
            self.response_worker_thread.join()

class RequestWorker:
    client: OfflineClient

    def __init__(self, parent=None, client=None, callback=None):
        self.client = client
        self.callback = callback

    def startWork(self):
        while True:
            # check if we are connected to server
            if not self.client.queue.empty():
                try:
                    msg = self.client.queue.get(timeout=1)
                except queue.Empty:
                    msg = None
                if msg == "quit":
                    # self.parent.quit_event.set(True)
                    # break
                    pass
                self.callback(msg)
            time.sleep(0.01)


class ResponseWorker:
    client: OfflineClient

    def __init__(self, parent=None, client=None):
        logger.set_level(LOG_LEVEL)
        self.client = client

    def startWork(self):
        while True:
            try:
                msg = self.client.res_queue.get(timeout=1)
            except queue.Empty:
                msg = None
            if msg != "" and msg is not None:
                self.client.handle_response(msg)
