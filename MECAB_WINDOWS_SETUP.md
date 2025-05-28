# MeCab Setup on Windows 11 for airunner (Japanese NLP)

This guide provides instructions for setting up MeCab and its related Python packages (`mecab-python3`, `fugashi`) on Windows 11 for Japanese language processing features in the airunner project, specifically for `openvoice_jp` capabilities.

## Overview

MeCab is a Japanese morphological analyzer. Setting it up on Windows involves installing MeCab binaries, a dictionary, and ensuring Python packages can interface with them. The `airunner` project lists `unidic` and `unidic-lite` (pip-installable dictionaries) and `mecab-python3`, `fugashi` (Python bindings) in its `setup.py` for Japanese support. `fugashi` is generally better at locating and using pip-installed dictionaries.

## Step 1: Install MeCab Binaries

Since there isn't an official, regularly updated MeCab binary installer for Windows from the original author, users often rely on community-provided or older versions.

**Recommended Approach:**

1.  **Download MeCab:**
    *   A commonly used version is `mecab-0.996.exe`. You can search for "mecab-0.996.exe download" from reliable sources. (Example placeholder: `[Link to a trusted MeCab 0.996 Windows binary source]`).
    *   Alternatively, some projects bundle MeCab or provide newer unofficial builds.
2.  **Run the Installer:**
    *   Execute the downloaded installer (e.g., `mecab-0.996.exe`).
    *   During installation, **pay attention to the installation directory**. A common path is `C:\Program Files\MeCab` or `C:\Program Files (x86)\MeCab`. Let's assume it's `C:\Program Files\MeCab`.
    *   The installer typically includes a version of the IPA dictionary and sets it as the default.
    *   **Character Set:** The installer might ask for the dictionary's character set. **UTF-8 is strongly recommended** for compatibility with modern systems and Python.

## Step 2: Configure Environment Variables

1.  **Add MeCab to PATH:**
    *   Add the MeCab `bin` directory (e.g., `C:\Program Files\MeCab\bin`) to your system's `PATH` environment variable. This allows Windows to find `mecab.exe` and, more importantly, `libmecab.dll`.
    *   To do this:
        1.  Press the Windows key, type "environment variables," and select "Edit the system environment variables."
        2.  Click "Environment Variables..."
        3.  Under "System variables," find and select `Path`, then click "Edit..."
        4.  Click "New" and add the path to your MeCab `bin` directory.
        5.  Click "OK" on all dialogs.
    *   You may need to restart your command prompt or IDE (and possibly Windows) for this change to take effect.

2.  **MECABRC Environment Variable (Optional but Recommended for Flexibility):**
    *   The `mecabrc` file is MeCab's configuration file. It specifies the dictionary directory (`dicdir`), among other settings.
    *   The installer usually places a `mecabrc` file in the MeCab installation directory (e.g., `C:\Program Files\MeCab\etc\mecabrc`).
    *   If you want to use a different dictionary or customize settings without modifying the installed files directly, you can:
        1.  Copy the original `mecabrc` to a user-writable location.
        2.  Set the `MECABRC` environment variable to point to the full path of your custom `mecabrc` file.
    *   This step is often not immediately necessary if `fugashi` is used with pip-installed dictionaries, but it's good practice for general MeCab usage.

## Step 3: Install Python Dictionaries and Bindings

The `airunner` project specifies these in `setup.py` under the `openvoice_jp` extra. If you install `airunner[openvoice_jp]`, these should be pulled in.

1.  **Install `unidic` and `unidic-lite` (Pip-installable Dictionaries):**
    ```bash
    python -m pip install unidic unidic-lite
    ```
    These packages provide versions of the UNIDIC dictionary that Python tools like `fugashi` can use.

2.  **Install `fugashi` and `mecab-python3`:**
    ```bash
    python -m pip install fugashi mecab-python3
    ```

## Step 4: How Python Packages Interact with MeCab

*   **`fugashi`:**
    *   `fugashi` is generally capable of finding MeCab if `libmecab.dll` is in the system `PATH`.
    *   It can also automatically detect and use pip-installed dictionaries like `unidic` or `unidic-lite`. You can often specify the dictionary to `fugashi` directly in code if needed, or it will use a sensible default (often the pip-installed one if available).
    *   No specific `MECABRC` configuration is usually required for `fugashi` to use a pip-installed `unidic`.

*   **`mecab-python3`:**
    *   This package is a more direct binding to `libmecab.dll`.
    *   It relies on the MeCab installation being "system-configured." This means `libmecab.dll` must be in the `PATH`.
    *   For dictionary usage, `mecab-python3` typically uses the dictionary that MeCab itself is configured to use (usually via the `dicdir` in the `mecabrc` file found by MeCab). It might not automatically use pip-installed dictionaries like `unidic` without further configuration of the main MeCab setup (i.e., making MeCab's `mecabrc` point to a system-wide UNIDIC installation).

**Recommendation for `airunner`:**
For Japanese support, relying on `fugashi` with a pip-installed `unidic` or `unidic-lite` is often the most straightforward path on Windows, as it minimizes complex system-wide MeCab dictionary configuration.

## Step 5: Verification

1.  **Command Line MeCab:**
    Open a new Command Prompt and type `mecab`. If the `PATH` is set correctly, MeCab should start. You can type some Japanese text to see if it's analyzed (it will likely use its default installed dictionary, e.g., IPA).
    ```
    C:\Users\YourUser> mecab
    これはテストです
    これ    名詞,代名詞,一般,*,*,*,これ,コレ,コレ
    は      助詞,係助詞,*,*,*,*,は,ハ,ワ
    テスト  名詞,サ変接続,*,*,*,*,テスト,テスト,テスト
    です    助動詞,*,*,*,特殊・デス,基本形,です,デス,デス
    EOS
    ```

2.  **Python `fugashi`:**
    ```python
    import fugashi
    # Fugashi should automatically find a dictionary,
    # prioritizing pip-installed ones like unidic if available.
    tagger = fugashi.Tagger()
    text = "これはテストです。"
    for word in tagger(text):
        print(f"{word.surface}\t{word.feature}")
    ```
    This should output analysis results, ideally using UNIDIC if `unidic` is installed.

3.  **Python `mecab-python3`:**
    ```python
    import MeCab
    # This will use MeCab's system-configured dictionary
    tagger = MeCab.Tagger()
    text = "これはテストです。"
    print(tagger.parse(text))
    ```
    This will use the dictionary MeCab is configured with (e.g., the IPA dictionary from the installer, unless `mecabrc` was modified).

## Troubleshooting

*   **`libmecab.dll` not found:** Ensure MeCab's `bin` directory is correctly added to `PATH` and that you've restarted your terminal/IDE.
*   **Dictionary not found (especially for `mecab-python3`):**
    *   Ensure MeCab was installed with a dictionary, or one was configured via `mecabrc`.
    *   The `mecabrc` file (e.g., in `C:\Program Files\MeCab\etc`) should have a correct `dicdir` entry pointing to the dictionary's directory (e.g., `dicdir = C:\Program Files\MeCab\dic\ipadic`).
    *   Ensure the dictionary files exist at that `dicdir` location.
    *   For `fugashi`, if it doesn't find `unidic`, ensure `unidic` or `unidic-lite` is properly installed in your Python environment.
*   **Character Encoding Issues:** Always prefer UTF-8 for dictionaries and MeCab configuration if possible. The MeCab Windows installer (0.996) defaults to UTF-8 for its bundled IPA dictionary.

This guide provides a general approach. Specific paths and download links for MeCab binaries may vary based on community availability.
