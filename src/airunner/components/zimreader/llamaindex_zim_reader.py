"""
LlamaIndex-compatible ZIM file reader for offline document ingestion.
"""

from typing import List
from pathlib import Path
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from airunner.components.zimreader.zimreader import ZIMReader


class LlamaIndexZIMReader(BaseReader):
    """LlamaIndex BaseReader for ZIM files using python-libzim."""

    def load_data(self, file: Path, **load_kwargs) -> List[Document]:
        zim = ZIMReader(str(file))
        documents = []
        for path in zim.search(""):
            html = zim.get_article(path)
            if html:
                documents.append(
                    Document(
                        text=html,
                        metadata={
                            "zim_path": path,
                            "zim_file": str(file),
                        },
                    )
                )
        return documents
