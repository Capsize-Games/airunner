"""PyInstaller hook: native library and JIT sources for mslk.

mslk loads its companion ``mslk.so`` by filesystem path
(``torch.ops.load_library`` on the sibling of ``__init__.py``),
invisible to static analysis -- and the default ``lib*.so``
collection pattern misses the bare ``mslk.so`` name, so it is
collected here explicitly. Without it the frozen daemon dies in
``import mslk`` inside the transformers/torchao chain (#2245).

``mslk.quantize.triton.fp8_quantize`` defines ``@triton.jit``
kernels, which read their own ``.py`` source at decoration time
(``inspect.getsourcelines`` fails on PYZ-only modules with
"should be defined in a Python file"). It ships in ``py`` mode --
imported from source -- mirroring hook-triton's treatment of
``triton.runtime.jit``.
"""

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs("mslk", search_patterns=["*.so"])

module_collection_mode = {
    "mslk.quantize.triton.fp8_quantize": "py",
}
