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
        """Load documents from a ZIM file.

        Args:
            file: Path to the ZIM file
            **load_kwargs: Optional keyword arguments
                - max_articles (int): Maximum number of articles to extract (default: 1000)

        Returns:
            List[Document]: List of LlamaIndex Document objects
        """
        max_articles = load_kwargs.get("max_articles", 1000)

        zim = ZIMReader(str(file))
        documents = []

        # Get all entry paths from the ZIM file (limited to avoid memory issues)
        paths = zim.get_all_entry_paths(limit=max_articles)

        for path in paths:
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
