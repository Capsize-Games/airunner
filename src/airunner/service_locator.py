import threading

from airunner.signal_mediator import SingletonMeta


class ServiceLocator(metaclass=SingletonMeta):
    _shared_state = {}
    _lock = threading.Lock()

    def __init__(self):
        self.__dict__ = self._shared_state
        if "_services" not in self.__dict__:
            self.__dict__["_services"] = {}

    @classmethod
    def register(cls, service_name, service):
        with cls._lock:
            instance = cls()
            instance._services[service_name] = service

    @classmethod
    def get(cls, service_name):
        with cls._lock:
            instance = cls()
            if service_name in instance._services:
                return instance._services[service_name]
            else:
                raise ValueError(f'Service not found: {service_name}')