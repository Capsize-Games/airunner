# Published upgrade baseline

CORE upgrade tests use this unmodified copy of the published `airunner`
`6.1.3-3` package. Its SHA-256 and size match the prior public APT package
inspection. CI verifies its digest, size, version and architecture before use.
The copy keeps the upgrade fixture reproducible when the original APT endpoint
is unavailable.

This is a test input, not a service runtime payload. The original package
contains its copyright/license notice and Python source. Its publisher did not
bind the binary package to a source revision; `provenance.json` retains that
unknown rather than inferring a source tag. No model or inference result is
established by this baseline.
