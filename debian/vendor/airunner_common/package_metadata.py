"""Canonical version and build metadata shared across AIRunner packages.

This module used to also hold the full services/native requirement
registries and setup-kwargs builders, read by ``services/setup.py`` and
``native/setup.py`` at build time. Both of those now vendor their own
metadata statically instead (issue #2038), and so does this repository's
own root ``setup.py`` (issue #2197, part of extracting this package into
its own repository) -- a build-time dependency on this module doesn't
survive a repository boundary, and every consumer needing these values
already keeps its own copy in sync per file docstring. What remains here
is only what real runtime code (not a ``setup.py``) actually imports.
"""

from __future__ import annotations

from pathlib import Path


# airunner-common is already live on PyPI at 6.1.3, published from
# Capsize-Games/airunner's own shared/ (this repository's origin, before
# extraction). This continues that version lineage rather than
# restarting at 0.1.0 like a genuinely new package would, since existing
# consumers (airunner-eval, airunner-tts-vendor, and this repository's
# own root/services/native setup.py files) already pin
# "airunner-common~=6.1" -- a version series break would need every one
# of those pins bumped in lockstep, defeating the point of extracting an
# independently-versioned foundation package in the first place.
VERSION = "6.1.7"

# Supply-chain hardening (issue #2036). This was a hash-pinned GitHub archive
# URL, but PyPI rejects any distribution carrying a PEP 440 direct reference
# ("400 Can't have direct dependency"), so no such package can ever be
# published. facehuggershield 1.0.0 is on PyPI, so depend on it by version.
#
# This does not weaken the original intent. That pin existed so "a tampered or
# moved tag cannot be substituted" -- but a git tag *can* be moved, which is
# exactly why it needed a digest. A PyPI release cannot: a version is immutable
# once uploaded and can only be yanked, never replaced. Installs also verify
# PyPI's own hashes over TLS. For a fully hash-locked install, pin digests in a
# requirements file at deploy time, which is where hash-locking belongs --
# install_requires cannot express it for consumers anyway.
FACEHUGGERSHIELD_REQUIREMENT = "facehuggershield==1.0.0"

# The project is GPL-3.0-only (issue #2058): the repo-root LICENSE file, every
# ``license=`` metadata field and these PyPI classifiers must agree. Vendored
# MIT/Apache-2.0 components (melo, openvoice, z_image) are compatible with GPL
# distribution; see THIRD_PARTY_NOTICES.md.
LICENSE_CLASSIFIERS = [
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
]

# This package lives at <repo>/airunner_common, so the repo root is one
# parent up in a checkout -- and the sdist carries the same layout (its
# root is the package's own repo root, via MANIFEST.in), so the same
# single candidate covers both cases. An installed wheel has no README at
# all, so fall back instead of crashing at import time (issue #2061).
def _resolve_readme() -> str:
    module_dir = Path(__file__).resolve().parent
    candidate = module_dir.parents[0] / "README.md"
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    # Installed wheel: no README ships with the runtime package. The wheel's
    # long_description was already baked from the sdist README at build time,
    # so a short placeholder here is only a defensive fallback.
    return "AI Runner shared foundation package."


README = _resolve_readme()


__all__ = [
    "FACEHUGGERSHIELD_REQUIREMENT",
    "LICENSE_CLASSIFIERS",
    "README",
    "VERSION",
]
