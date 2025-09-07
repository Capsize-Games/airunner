"""
Custom EPUB reader for EPUBs with numbered page structure
"""

import os
import zipfile
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.core.readers.base import BaseReader


class CustomEpubReader(BaseReader):
    """Custom EPUB reader that handles numbered page structure"""

    def load_data(
        self, file: Optional[str] = None, **kwargs
    ) -> List[Document]:
        """Load data from EPUB file."""
        if not file or not os.path.exists(file):
            return []

        documents = []

        try:
            with zipfile.ZipFile(file, "r") as zip_file:
                # Get all HTML files in order
                html_files = [
                    f
                    for f in zip_file.namelist()
                    if f.endswith((".html", ".xhtml", ".htm"))
                ]

                # Sort page files numerically if they follow page_X.html pattern
                page_files = [
                    f
                    for f in html_files
                    if "page_" in f and not f.endswith("nav.xhtml")
                ]
                page_files.sort(key=lambda x: self._extract_page_number(x))

                # If no page files, fall back to all HTML files
                if not page_files:
                    page_files = html_files

                all_content = []

                for html_file in page_files:
                    try:
                        with zip_file.open(html_file) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            soup = BeautifulSoup(content, "html.parser")
                            text = soup.get_text()
                            cleaned_text = " ".join(text.split())

                            if cleaned_text and len(cleaned_text.strip()) > 10:
                                all_content.append(cleaned_text)

                    except Exception as e:
                        print(f"Warning: Could not read {html_file}: {e}")
                        continue

                # Combine all content into a single document
                if all_content:
                    full_text = "\n\n".join(all_content)
                    metadata = {
                        "file_path": file,
                        "file_name": os.path.basename(file),
                        "file_type": "application/epub+zip",
                        "pages_processed": len(all_content),
                    }

                    documents.append(
                        Document(text=full_text, metadata=metadata)
                    )

        except Exception as e:
            print(f"Error reading EPUB {file}: {e}")

        return documents

    def _extract_page_number(self, filename: str) -> int:
        """Extract page number from filename like 'EPUB/page_123.html'"""
        try:
            # Extract number from page_X.html pattern
            parts = filename.split("page_")
            if len(parts) > 1:
                number_part = parts[1].split(".")[0]
                return int(number_part)
        except (ValueError, IndexError):
            pass
        return 0
