"""
RabbitMQ backend for SignalMediator.

This requires the pika library to be installed.

"""

from typing import Callable, Dict
from airunner.enums import SignalCode


class RabbitMQBackend:
    """
    RabbitMQ-based backend for SignalMediator.
    """

    def __init__(self, username: str, password: str, url: str, port: int):
        import pika

        rabbitmq_url = f"amqp://{username}:{password}@{url}:{port}/"
        self.rabbitmq_url = rabbitmq_url
        self.connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        self.channel = self.connection.channel()
        self.handlers: Dict[str, Callable] = {}

    def register(self, code: SignalCode, handler: Callable):
        """
        Register a handler for a specific SignalCode.
        """
        queue_name = code.value
        self.handlers[queue_name] = handler
        self.channel.queue_declare(queue=queue_name)

        def callback(ch, method, properties, body):
            handler(body)

        self.channel.basic_consume(
            queue=queue_name, on_message_callback=callback, auto_ack=True
        )

    def emit_signal(self, code: SignalCode, data: dict):
        """
        Publish a message to the RabbitMQ queue.
        """
        queue_name = code.value
        self.channel.queue_declare(queue=queue_name)
        self.channel.basic_publish(
            exchange="", routing_key=queue_name, body=str(data)
        )

    def start_consuming(self):
        """
        Start consuming messages from RabbitMQ.
        """
        self.channel.start_consuming()

    def close(self):
        """
        Close the RabbitMQ connection.
        """
        self.connection.close()
