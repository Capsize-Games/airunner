import json
import queue
import time
import threading

from airunner.aihandler.engine import Engine
from airunner.aihandler.logger import Logger as logger


class OfflineClient:
    sd_runner = None
    app = None
    current_txt2img_model = None
    current_inpaint_model = None
    do_base64: bool = False
    response_worker = None
    request_worker = None
    response_worker_thread = None
    request_worker_thread = None

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
        self.do_base64 = kwargs.get("do_base64", None)
        self.app = kwargs.get("app", None)
        self.queue = queue.Queue()
        self.res_queue = queue.Queue()
        self.message_var = kwargs.get("message_var")
        self.message_handler = kwargs.get("message_handler")
        self.stop_event = threading.Event()
        self.do_start()

    def stop(self):
        self.stop_event.set()

    def stopped(self):
        return self.stop_event.is_set()

    def do_start(self):
        logger.info("Starting client")
        self.init_sd_runner()
        self.force_request_worker_reset()

    def init_sd_runner(self):
        logger.info("Initializing AI Runner")
        self.sd_runner = Engine(
            app=self.app,
            message_var=self.message_var,
            message_handler=self.message_handler
        )

    def handle_response(self, response):
        res = json.loads(response.decode("utf-8"))
        if "response" in res:
            self.response = response
        else:
            self.message = response

    def handle_error(self, error):
        logger.error(error)

    def callback(self, data):
        action = data.get("action")
        model = data["options"][f"model"]

        data["do_base64"] = self.do_base64

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
                self.sd_runner.sd.initialized = False
                self.sd_runner.sd.reload_model = True

        if (action in ("txt2img", "img2img") and self.sd_runner.sd.action in ("inpaint", "outpaint")) or \
            (action in ("inpaint", "outpaint") and self.sd_runner.sd.action in ("txt2img", "img2img")):
            self.sd_runner.sd.initialized = False

        self.sd_runner.generator_sample(data)

    def create_worker_thread(self):
        self.response_worker = ResponseWorker(client=self)
        self.request_worker = RequestWorker(client=self, callback=self.callback)
        self.response_worker_thread = threading.Thread(target=self.response_worker.startWork)
        self.request_worker_thread = threading.Thread(target=self.request_worker.startWork)
        self.response_worker_thread.start()
        self.request_worker_thread.start()

    def force_request_worker_reset(self):
        if self.request_worker_thread and self.request_worker_thread.is_alive():
            self.request_worker_thread.join()

        if self.response_worker_thread and self.response_worker_thread.is_alive():
            self.response_worker_thread.join()

        self.create_worker_thread()

    def force_request_worker_quit(self):
        if self.request_worker_thread and self.request_worker_thread.is_alive():
            self.request_worker_thread.join()


class RequestWorker:
    def __init__(self, client=None, callback=None):
        self.client = client
        self.callback = callback

    def startWork(self):
        while not self.client.stopped():
            if not self.client.queue.empty():
                try:
                    msg = self.client.queue.get(timeout=1)
                except queue.Empty:
                    msg = None
                if msg == "quit":
                    pass
                self.callback(msg)
            time.sleep(0.01)


class ResponseWorker:
    def __init__(self, client=None):
        self.client = client

    def startWork(self):
        while not self.client.stopped():
            try:
                msg = self.client.res_queue.get(timeout=1)
            except queue.Empty:
                msg = None
            if msg != "" and msg is not None:
                self.client.handle_response(msg)