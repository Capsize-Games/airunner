"""The desktop/daemon wire contract version (issue #2192).

Before this module existed, nothing versioned the contract in
services/src/airunner_services/runtimes/contracts.py. The desktop and
daemon processes were always the same commit inside one repository,
so an incompatible pair could only happen mid-development, and it
failed with an arbitrary attribute error at an arbitrary point in a
conversation rather than being refused at connection time. Both of
those assumptions stop holding once the desktop/daemon boundary can
cross a repository boundary (see #2185's Phase 3).

This version is independent of any single distribution's own package
version (see docs/architecture/versioning-and-compatibility-policy.md,
issue #2191): the contract changes far less often than either
airunner or airunner-services' own code, so tying it to either
package's version would force unrelated releases every time one of
them bumped for a reason that had nothing to do with the wire format.

Compatibility rule: two contract versions are compatible exactly when
their major component matches. A minor or patch bump must only add
optional fields, add enum members, or add new message types -- never
remove a field, remove an enum member, or change a field's type or
required-ness. Any change of that kind is a major bump. This mirrors
the ``~=X.Y`` policy #2191 sets for ordinary package dependencies,
applied to the one edge that isn't an ordinary package dependency.
"""

from __future__ import annotations

CONTRACT_VERSION = "1.0.0"


def _major(version: str) -> str:
    return version.split(".", 1)[0]


def is_compatible_contract_version(local: str, remote: str) -> bool:
    """Return whether two contract versions may safely talk to each other."""
    return _major(local) == _major(remote)
