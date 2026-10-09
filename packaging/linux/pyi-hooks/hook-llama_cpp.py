"""PyInstaller hook: versioned shared libraries for llama_cpp.

llama_cpp loads ``libllama.so`` from ``llama_cpp/lib/`` by path via
ctypes; that library's DT_NEEDED entries name versioned SONAMEs
(``libggml.so.0``, ...). ``--collect-binaries`` only matches
``lib*.so``, so the versioned files would be missing and the load
would fail at runtime. This hook collects the full ``lib/`` set.
"""

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs(
    "llama_cpp", search_patterns=["*.so", "*.so.*"]
)
