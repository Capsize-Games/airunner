class ServiceLocator:
    _services = {}

    @staticmethod
    def register(service_name, service):
        ServiceLocator._services[service_name] = service

    @staticmethod
    def get(service_name):
        if service_name in ServiceLocator._services:
            return ServiceLocator._services[service_name]
        else:
            raise ValueError(f'Service not found: {service_name}')