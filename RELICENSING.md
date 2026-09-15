# Licensing history

AI Runner is distributed under the **GNU General Public License v3.0 only**
(`GPL-3.0-only`). See [LICENSE](LICENSE) for the full text and
[NOTICE](NOTICE) for the copyright statement.

## Why this file exists

Two things about the licence were previously ambiguous, and this records the
answers so nobody has to guess.

### 1. The repository reported "Other" instead of GPL-3.0

`LICENSE` contained the complete, unmodified GPL-3.0 text with one extra line
prepended above it:

```
Airunner — Copyright (C) 2026 Capsize LLC
```

GitHub, and most SBOM and licence-scanning tooling, identify a licence by
matching a file's text against known templates. That one line was enough to
break the match, so the GitHub API reported `NOASSERTION`, the repository badge
read "Other", and automated scanners saw an unidentifiable licence on a project
with over a thousand dependents and forks. For anyone whose employer requires a
licence review before adopting a dependency, "unidentifiable" is a stop.

The copyright line moved to [NOTICE](NOTICE) and `LICENSE` is now byte-identical
to the canonical GPL-3.0 text. Nothing about the terms changed.

### 2. The project was MIT before 2026

| Period | Licence | Copyright holder |
|---|---|---|
| 2023 – 2024 | MIT | Capsize Games |
| 2026 – | GPL-3.0-only | Capsize LLC |

MIT is GPL-compatible, so relicensing MIT-covered code under GPL-3.0 is
permitted and no contributor's permission was required for it.

**If you forked or vendored AI Runner while it was MIT, your rights to the code
as it stood at that time are unaffected.** MIT grants are irrevocable; this
relicensing applies going forward, not retroactively. You may continue to use
that earlier code under MIT. Code added from 2026 onward is GPL-3.0-only.

If you are unsure which terms apply to a particular commit, the licence in
effect is whatever `LICENSE` contained at that commit.
