# Versioning and compatibility policy

Status: policy decision for the repo-split work tracked in
[#2185](https://github.com/Capsize-Games/airunner/issues/2185). No
code changes required by this document alone; it is the answer that
[#2192](https://github.com/Capsize-Games/airunner/issues/2192)
(contract versioning) and
[#2200](https://github.com/Capsize-Games/airunner/issues/2200) (release
orchestration) build the mechanics for. Written 2026-09-17 against
`8577ffdd3`.

## Current state

`shared/airunner_common/package_metadata.py` single-sources one
`VERSION = "6.1.3"` for all four in-tree distributions. The root
`setup.py` and `services/setup.py` both pin their siblings by exact
equality: `f"airunner-common=={VERSION}"`,
`f"airunner-services=={VERSION}"`. `native/setup.py` follows the same
pattern via a `sys.path` insert into `shared/`.

That file also single-sources three things that are not the version:

- `FACEHUGGERSHIELD_REQUIREMENT` -- a supply-chain-hardening pin
  (issue #2036), documented in the file as intentionally shared so no
  distribution can carry a weaker pin than the others.
- `LICENSE_CLASSIFIERS` -- the GPL-3.0-only classifier every
  distribution's `setup()` call must agree with (issue #2058).
- `DEVELOPMENT_REQUIREMENTS` -- shared dev/test tooling (`pytest`,
  `black`, `mypy`, ...), used by more than one surface's install.

Exact-equality pins are the right call inside one repository: one
commit changes `VERSION` and every consumer moves together, with no
version skew possible. Across repositories the same pins become the
worst possible choice: every repository pays the cross-repo cost
(separate PRs, separate CI runs, a release train to coordinate) and
none of them get the benefit, because no consumer can ever accept a
newer sibling without every other distribution being re-released at
the same moment. Splitting the repositories without changing this
would make the project strictly worse than the monorepo it replaces.

## 1. Independent versioning

**Decision: `airunner-common`, `airunner-native` and
`airunner-tts-vendor` version independently.
`airunner` and `airunner-services` also version independently of each
other**, with the coupling that matters -- which exact pair was tested
together -- enforced by the release lockfile (#2200), not by sharing a
version number.

Reasoning:

- `airunner-common`, `airunner-native` and `airunner-tts-vendor` are
  pure foundation/leaf packages: nothing they depend on lives in this
  project, and they change for reasons (a settings default, a sidecar
  pin, an upstream MeloTTS sync) that are unrelated to a desktop
  release. Coupling their version to the application's forces a
  release of all three every time the application ships, for no
  reason tied to their own content.
- `airunner` and `airunner-services` are more tempting to keep
  coupled, since they ship together as one product. But they already
  change at different rates today -- `services/` carries roughly four
  times the desktop's line count and the bulk of the Linux v1 release
  work (#2083) -- and forcing them to share a version number recreates
  the exact problem this policy exists to avoid: a services-only fix
  would force a version bump (and a release) of the desktop
  application too. The daemon/desktop compatibility question this
  raises is real, which is exactly why #2192 exists: the contract
  between them is versioned and checked at connection time,
  independently of either distribution's own package version.
- `airunner-eval` versions independently; nothing depends on it.

## 2. Pin style per edge

| Edge | Pin style | Why |
|---|---|---|
| `airunner-native` -> `airunner-common` | `~=X.Y` (compatible release) | Foundation types change rarely; a native build should pick up patch fixes without a manual bump. |
| `airunner-tts-vendor` -> `airunner-common` | `~=X.Y` | Same reasoning; the vendor fork already treats `airunner_common` as a stable, narrow surface (issue #2190's resolver pattern is the entire integration point). |
| `airunner-services` -> `airunner-common` | `~=X.Y` | Same reasoning. |
| `airunner-services` -> `airunner-tts-vendor` | `~=X.Y` | The fork's public surface (issue #2195) is small and deliberately kept stable. |
| `airunner` -> `airunner-common` | `~=X.Y` | Same reasoning. |
| `airunner` -> `airunner-native` | `~=X.Y` | The desktop only needs the launcher/crash-handler surface, which changes rarely. |
| `airunner` -> `airunner-services` | Exact (`==X.Y.Z`) in the **released bundle only**; `~=X.Y` in ordinary development | This is the one wire contract with real compatibility risk (issue #2192). Development should not need a matching services release for every desktop commit, but the shipped bundle must not resolve a range at install time -- see the shipped-artifact constraint below. |

`~=X.Y` (PEP 440 compatible release) means "any version compatible
with `X.Y`", which allows patch and minor updates but not a breaking
major bump, consistent with each package also committing to semantic
versioning under this policy (a major version bump is the only bump
allowed to break a consumer).

## 3. Compatibility window

Each independently-versioned package supports **the current minor
version plus one prior minor version** for its own consumers, except
the desktop/daemon edge, which #2192 governs separately with an
explicit protocol version and a connection-time handshake rather than
a package-version compatibility window. A breaking change to
`airunner_common.contract_enums` is a major version bump under this
policy, and #2192's protocol version is the mechanism that catches an
enum drift at connection time rather than at an arbitrary point
mid-conversation.

## 4. Breaking-change procedure

1. The change lands in the owning repository behind a major version
   bump (per semver, since this policy commits every package to it).
2. Every direct consumer's pin (`~=X.Y` per the table above) is
   updated in the same pull request that bumps its own dependency, not
   discovered later by a failing build. #2200's cross-repo integration
   build is the backstop for a consumer nobody updated in time.
3. The desktop installer never resolves a version range at install
   time. It always installs from the release lockfile (#2200), so a
   breaking change reaches a customer only through a new signed
   release candidate that was built and tested with the new pin, never
   through an in-place dependency upgrade on an existing install.
4. `airunner_common.contract_enums` changes get one additional step
   before any of the above: read against #2192's compatibility rule
   for what counts as a breaking change to the wire contract
   specifically (adding an enum member, for instance, is likely
   additive; changing a member's value is not).

## 5. The customer-facing version

**The customer-facing version is `airunner`'s own version.** It is
what `pip install airunner` reports, what the installed bundle's
about dialog shows, and what #2119 (P10, update verification) and
#2116 (P07, transactional upgrades) key off when deciding whether a
downloaded update is newer than the installed one. Every sibling
version the release was built against is recorded in the release
lockfile (#2200) and surfaces in diagnostics, but a customer never
needs to reason about `airunner-services`' version number directly.

## Constraints this policy does not relax

- **The shipped bundle stays fully locked**, regardless of the ranges
  this policy allows for ordinary development. #2200 is where "resolve
  a compatible range" and "install from an exact, tested lockfile"
  are kept distinct; this policy only says what the range is allowed
  to be during development, never at release time.
- **No release requires a human to hand-edit four files.** The
  version-bump-and-repin sequence in step 2 above is exactly the kind
  of mechanical step #2200's release orchestration should automate,
  not a manual checklist repeated every release.

## Disposition of `package_metadata.py`'s other constants

Once `airunner-common` is its own repository (#2197), the other three
single-sourced constants move as follows:

- **`FACEHUGGERSHIELD_REQUIREMENT`** moves with `VERSION` -- it stays
  in the published `airunner-common` package. It is exactly the kind
  of cross-cutting, security-relevant pin this policy's independent
  foundation-package versioning exists to keep synchronized without
  coupling it to the application's release cadence.
- **`LICENSE_CLASSIFIERS`** also moves with `VERSION` and stays
  published. Every consumer importing it at build time and asserting
  it matches their own `setup()` call is a cheap, mechanical way to
  keep GPL-3.0 declared consistently across six repositories instead
  of five separate places it could silently drift (issue #2058 is
  exactly the failure mode this prevents recurring).
- **`DEVELOPMENT_REQUIREMENTS`** does **not** belong in a runtime
  distribution's metadata and should not move with the other two. It
  is build/test tooling (`pytest`, `black`, `mypy`, `pyinstaller`),
  not something a runtime consumer of `airunner-common` needs.
  Recommendation: each repository declares its own `development`
  extra in its own `setup.py`, accepting that the tool *versions* may
  drift slightly between repositories (already possible today within
  a single repo's own extras, since nothing enforces one `black`
  pin project-wide beyond this file). If keeping a single shared
  set of tool pins turns out to matter in practice, a small
  `airunner-dev-requirements` package is the option to reach for --
  not bundling it into the foundation package every runtime consumer
  installs.

## Known documentation staleness found while writing this policy

`docs/architecture/package_split_contract.md` states "Shared runtime
contracts and enums live in `airunner_services.contract_enums`". That
module does not exist; the real location is
`shared/airunner_common/contract_enums.py` (confirmed: `find
services/src/airunner_services -maxdepth 1 -iname contract_enums.py`
returns nothing). That document predates the `shared/` package split
and was not updated when `contract_enums` moved. Corrected in the
same commit as this policy since both touch the same document
neighborhood.
