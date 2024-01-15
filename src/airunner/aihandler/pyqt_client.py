import json
import queue
import time
from PyQt6 import QtCore
from PyQt6.QtCore import QThread
from airunner.aihandler.engine import Engine

from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.qtvar import BooleanVar
from airunner.aihandler.runner import SDRunner


class OfflineClient(QtCore.QObject):
    sd_runner = None
    app = None
    current_txt2img_model = None
    current_inpaint_model = None
    request_signal_status = QtCore.pyqtSignal(str)
    response_signal_status = QtCore.pyqtSignal(str)
    response_worker = None
    request_worker = None
    response_worker_thread = None
    request_worker_thread = None
    do_base64: bool = False
    do_process_queue: bool = True

    @property
    def engine(self):
        return self.sd_runner

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
        logger.info("Canceling")
        self.sd_runner.cancel()
        while not self.queue.empty():
            self.queue.get()

    def __init__(self, **kwargs):
        super().__init__(
            parent=kwargs.get("parent", None)
        )
        self.do_base64 = kwargs.get("do_base64", None)
        self.app = kwargs.get("app", None)
        self.quit_event = BooleanVar()
        self.queue = queue.Queue()
        self.res_queue = queue.Queue()
        self.quit_event.set(False)
        self.message_var = kwargs.get("message_var")
        self.message_handler = kwargs.get("message_handler")
        self.do_start()

    def do_start(self):
        # create a stable diffusion runner service
        logger.info("Starting offline client")
        self.init_sd_runner()
        self.force_request_worker_reset()

    def init_sd_runner(self):
        # save sd_runner to disc and load from it next time
        # this is to avoid the overhead of creating a new sd_runner
        # every time we start the client
        logger.info("Initialzing SDRunner")
        self.sd_runner = Engine(
            app=self.app,
            message_var=self.message_var,
            message_handler=self.message_handler
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
        logger.error(error)

    def callback(self, data):
        data["do_base64"] = self.do_base64
        self.sd_runner.generator_sample(data)

    def create_worker_thread(self):
        # start worker in a new thread using the self.worker method
        self.response_worker = ResponseWorker(client=self)
        self.request_worker = RequestWorker(client=self, callback=self.callback)
        self.response_worker_thread = QThread()
        self.response_worker_thread.started.connect(self.response_worker.startWork)
        self.request_worker_thread = QThread()
        self.request_worker_thread.started.connect(self.request_worker.startWork)
        self.response_worker_thread.start()
        self.request_worker_thread.start()
        self.response_worker.moveToThread(self.response_worker_thread)
        self.request_worker.moveToThread(self.request_worker_thread)
        self.response_worker.signalStatus.connect(self.request_signal_status)
        self.request_worker.signalStatus.connect(self.response_signal_status)

    def force_request_worker_reset(self):
        if self.request_worker_thread and self.request_worker_thread.isRunning():
            print('Terminating thread.')
            self.request_worker_thread.terminate()

            print('Waiting for thread termination.')
            self.request_worker_thread.wait()

            self.request_signal_status.emit('Idle.')

        if self.response_worker_thread and self.response_worker_thread.isRunning():
            print('Terminating thread.')
            self.response_worker_thread.terminate()

            print('Waiting for thread termination.')
            self.response_worker_thread.wait()

            self.response_signal_status.emit('Idle.')

        self.create_worker_thread()

    def force_request_worker_quit(self):
        if self.request_worker_thread.isRunning():
            self.request_worker_thread.terminate()
            self.request_worker_thread.wait()


class RequestWorker(QtCore.QObject):
    client: OfflineClient
    signalStatus = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, client=None, callback=None):
        self.client = client
        super(self.__class__, self).__init__(None)
        self.callback = callback

    @QtCore.pyqtSlot()
    def startWork(self):
        while True:
            # check if we are connected to server
            if not self.client.queue.empty() and self.client.do_process_queue:
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


class ResponseWorker(QtCore.QObject):
    client: OfflineClient
    signalStatus = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, client=None):
        self.client = client
        super(self.__class__, self).__init__(parent)

    @QtCore.pyqtSlot()
    def startWork(self):
        while True:
            try:
                msg = self.client.res_queue.get(timeout=1)
            except queue.Empty:
                msg = None
            if msg != "" and msg is not None:
                self.client.handle_response(msg)
