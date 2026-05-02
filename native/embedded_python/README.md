# Embedded Python Pins

This directory pins the embedded Python runtimes used by AIRunner's
end-user bundle builders.

Current policy:
- Linux bundles use Astral's `python-build-standalone` install-only runtime
- Windows bundles use Astral's `python-build-standalone` install-only runtime
- both platforms stay pinned to the same CPython version and release tag

The bundle builder copies this pin file into `share/airunner/` so shipped
artifacts record the exact embedded Python input that produced them.