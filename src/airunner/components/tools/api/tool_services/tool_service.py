from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.components.tools.api.tool_services.search import search


class ToolService(APIServiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def search(inp):
        return search(inp)
