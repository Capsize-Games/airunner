import signal
import socket
import json
import time

from airunner.aihandler.enums import EngineResponseCode
from airunner.aihandler.logger import Logger as logger


class SocketServer:
    client_socket = None
    server_socket = None

    def __init__(self, **kwargs):
        self.keep_alive = kwargs.get("keep_alive", False)
        self.host = kwargs.get("host")
        self.port = kwargs.get("port")
        self.packet_size = kwargs.get("packet_size", 1024)
        self.engine = Engine(
            do_base64=True,
            message_handler=self.message_handler
        )
        logger.info("Starting server")
        logger.info(f"Listening at {self.host}:{self.port}")
        self.start_server()
        self.connect("image_generated_signal", self)

    def start_server(self):
        if self.engine.stopped():
            return
        try:
            self.start()
            self.run()
        except socket.timeout:
            if self.keep_alive:
                self.stop()
                self.start_server()
            else:
                logger.info("Socket timeout")
                self.close_server(None, None)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # set SO_REUSEADDR option
        self.server_socket.bind((self.host, int(self.port)))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1)
        signal.signal(signal.SIGINT, self.close_server)

    def run(self):
        self.running = True
        # set a timeout on client_socket.recv so that we can check if the server is still running
        (self.engine_socket, self.engine_address) = self.server_socket.accept()
        self.engine_socket.settimeout(1)
        logger.info(f"Client connected from {self.engine_address}")
        packets = []
        while self.running:
            try:
                data = self.engine_socket.recv(self.packet_size)
                if data == b'':
                    break
                # get data in packet_size packets until we get a packet_size byte zero chunk
                if data == b'\x00' * self.packet_size:
                    # we have received the end of the message
                    logger.info("Received end message")
                    data = b''.join(packets)
                    # strip x00 padding
                    data = data.rstrip(b'\x00')
                    packets = []
                    try:
                        self.engine.do_request(json.loads(data.decode("utf-8")))
                    except json.decoder.JSONDecodeError:
                        logger.error("Invalid json in request")
                    continue
                else:
                    packets.append(data)
            except socket.timeout:
                continue
            time.sleep(0.01)
        self.start_server()

    def process_response(self, response: dict):
        # convert response to json string
        response = json.dumps(response)
        # convert response to bytes
        response = response.encode()
        # pad the response if it is less than packet_size
        response = self.pad_packet(response)
        # create the packets
        packets = [response[i:i + self.packet_size] for i in range(0, len(response), self.packet_size)]
        return packets

    def pad_packet(self, packet):
        if len(packet) < self.packet_size:
            packet += b' ' * (self.packet_size - len(packet))
        return packet

    def message_handler(self, response: dict):
        try:
            code = response["code"]
        except TypeError:
            # logger.error(f"Invalid response message: {response}")
            # traceback.print_exc()
            return
        message = response["message"]
        {
            EngineResponseCode.STATUS: self.handle_status,
            EngineResponseCode.ERROR: self.handle_error,
            EngineResponseCode.PROGRESS: self.handle_progress,
            EngineResponseCode.EMBEDDING_LOAD_FAILED: self.handle_embedding_load_failed,
        }.get(code, self.handle_unknown)(message)

    def handle_status(self, message):
        print(message)

    def handle_progress(self, message):
        self.send_response(message)

    def handle_error(self, message):
        print(message)

    def on_image_generated_signal(self, message):
        logger.info("Image generated")
        self.send_response(message)

    def handle_embedding_load_failed(self, message):
        print(message)

    def handle_unknown(self, message):
        print(message)

    def send_response(self, response):
        packets = self.process_response(response)
        for packet in packets:
            packet = self.pad_packet(packet)
            self.engine_socket.sendall(packet)
        self.send_end_message()

    def send_end_message(self):
        # send a packet_size byte zero chunk to indicate the end of the message
        self.engine_socket.sendall(b'\x00' * self.packet_size)

    def stop(self):
        if self.engine_socket:
            self.engine_socket.close()
        if self.server_socket:
            self.server_socket.close()
        self.running = False
        time.sleep(2)

    def close_server(self, signal=None, frame=None):
        logger.info("stopping threads")
        self.engine.stop()
        logger.info("waiting for response worker thread")
        self.engine.response_worker_thread.join()
        logger.info("waiting for request worker thread")
        self.engine.request_worker_thread.join()
        logger.info("Closing server")
        self.stop()
        logger.info("Exiting")

