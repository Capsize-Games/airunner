import cv2
from PIL import Image
from PySide6.QtCore import QThread

from airunner.enums import SignalCode, QueueType, WorkerState
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class VisionCaptureWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_type = QueueType.NONE
        self.cap = None
        self.locked = False
        self.register(SignalCode.VISION_START_CAPTURE, self.start_vision_capture)
        self.register(SignalCode.VISION_STOP_CAPTURE, self.stop_capturing)
        self.register(SignalCode.VISION_CAPTURE_UNPAUSE_SIGNAL, self.unpause)
        self.register(SignalCode.VISION_CAPTURE_PAUSE_SIGNAL, self.pause)
        self.register(SignalCode.VISION_CAPTURE_UNLOCK_SIGNAL, self.unlock)
        self.register(SignalCode.VISION_CAPTURE_LOCK_SIGNAL, self.lock)

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def start_vision_capture(self, message):
        """
        Starts capturing images
        :param message:
        :return:
        """
        self.state = WorkerState.RUNNING

    def stop_capturing(self):
        """
        Stops capturing images
        :return:
        """
        self.state = WorkerState.HALTED

    def start(self):
        self.logger.debug("Starting")

        if self.settings["ocr_enabled"]:
            self.enable_cam()
        else:
            self.state = WorkerState.HALTED

        self.running = True
        while self.running:
            if self.state == WorkerState.RUNNING:
                self.emit_signal(SignalCode.VISION_CAPTURED_SIGNAL, {
                    "image": self.capture_image()
                })
                self.state = WorkerState.PAUSED
                QThread.msleep(SLEEP_TIME_IN_MS)

            while self.state == WorkerState.PAUSED or self.locked:
                QThread.msleep(SLEEP_TIME_IN_MS)

            if self.state == WorkerState.HALTED:
                self.disable_cam()
                while self.state == WorkerState.HALTED:
                    QThread.msleep(SLEEP_TIME_IN_MS)
                self.enable_cam()

            if self.state != WorkerState.RUNNING:
                QThread.msleep(SLEEP_TIME_IN_MS)

    def enable_cam(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.logger.error("Unable to open camera")
            self.state = WorkerState.HALTED

    def disable_cam(self):
        if self.cap:
            self.cap.release()

    def capture_image(self):
        """
        Captures an image from active camera and returns it
        :return:
        """
        if not self.cap:
            return

        # Capture frame-by-frame
        ret, frame = self.cap.read()

        """
        Resize image to 768x768 cropped from the center
        """
        resized_frame = self.resize_image(frame)

        return Image.fromarray(cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB))

    def resize_image(self, image):
        """
        Resize image to 768x768 cropped from the center
        :param image:
        :return:
        """
        resize_width, resize_height = 570, 380
        height, width, channels = image.shape
        if height > width:
            diff = height - width
            image = image[diff // 2:-diff // 2, :]
        elif width > height:
            diff = width - height
            image = image[:, diff // 2:-diff // 2]
        return cv2.resize(image, (resize_width, resize_height))