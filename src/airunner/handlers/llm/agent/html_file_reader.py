from abc import ABCMeta, ABC

from bs4 import BeautifulSoup
from llama_index.core.readers.base import BasePydanticReader
from llama_index.core.schema import Document

BasePydanticReaderMeta = type(BasePydanticReader)


class CombinedMeta(BasePydanticReaderMeta, ABCMeta):
    pass


class HtmlFileReader(BasePydanticReader, ABC, metaclass=CombinedMeta):
    @staticmethod
    def read(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text()

    def load_data(self, *args, **load_kwargs):
        documents = []
        file_path = load_kwargs["extra_info"]["file_path"]
        documents.append(Document(
            text=self.read(file_path),
            id_=load_kwargs["extra_info"]["file_name"],
            metadata=load_kwargs["extra_info"])
        )
        return documents
