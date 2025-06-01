from airunner.api.api_service_base import APIServiceBase
from airunner.api.tool_services.search import search


class ToolService(APIServiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def search(inp):
        return search(inp)
