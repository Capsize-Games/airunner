#!/usr/bin/env python
import nltk

from airunner.settings import NLTK_DOWNLOAD_DIR

nltk.data.path.append(NLTK_DOWNLOAD_DIR)

nltk.download("stopwords", download_dir=NLTK_DOWNLOAD_DIR, quiet=True, halt_on_error=False, raise_on_error=False)
nltk.download("punkt", download_dir=NLTK_DOWNLOAD_DIR, quiet=True, halt_on_error=False, raise_on_error=False)
