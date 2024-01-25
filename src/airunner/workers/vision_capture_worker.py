import time
import cv2
from PIL import Image
from PyQt6.QtCore import QThread

from airunner.aihandler.enums import WorkerCode, SignalCode, QueueType
from airunner.workers.worker import Worker


class VisionCaptureWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_type = QueueType.NONE
        self.cap = None
        self.pause = False
        self.halted = False
        self.is_capturing = False
        self.interval = 1  # the amount of seconds between each image capture
        self.register(SignalCode.START_VISION_CAPTURE, self, self.start_vision_capture)
        self.register(SignalCode.STOP_VISION_CAPTURE, self, self.stop_capturing)
        self.register(SignalCode.VISION_CAPTURE_UNPAUSE_SIGNAL, self, self.unpause)

    def unpause(self, _message):
        self.pause = False
    
    def start_vision_capture(self, message):
        self.halted = False

    def stop_capturing(self):
        self.halted = True

    def start(self):
        if not self.settings["ocr_enabled"]:
            self.pause = True
        self.logger.info("Starting")
        self.is_capturing = True
        self.enable_cam()
        while self.is_capturing:
            if not self.pause:
                self.logger.info("capturing...")
                self.emit(SignalCode.VISION_CAPTURED_SIGNAL, dict(
                    image=self.capture_image()
                ))
                self.pause = True
                QThread.msleep(self.interval)

            while self.pause:
                QThread.msleep(100)

            if self.halted:
                self.disable_cam()
                while self.halted:
                    QThread.msleep(100)
                self.enable_cam()
        self.disable_cam()

    def enable_cam(self):
        # Open the webcam
        self.cap = cv2.VideoCapture(0)
        # Check if the webcam is opened correctly
        if not self.cap.isOpened():
            raise IOError("Unable to open webcam")

    def disable_cam(self):
        # When everything done, release the capture and destroy the window
        self.cap.release()

    def capture_image(self):
        """
        Captures an image from active camera and returns it
        :return:
        """
        self.logger.info("Capturing image")

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