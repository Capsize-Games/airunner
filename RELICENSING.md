# Licensing history

AI Runner is distributed under the **Apache License 2.0**
(`Apache-2.0`) as of 2026-11-28. See [LICENSE](LICENSE) for the full text and
[NOTICE](NOTICE) for the copyright statement.

## Why this file exists

Two things about the licence were previously ambiguous, and this records the
answers so nobody has to guess.

### 1. The repository reported "Other" instead of its licence

`LICENSE` once contained the complete licence text with one extra line
prepended above it:

```
Airunner — Copyright (C) 2026 Capsize LLC
```

GitHub, and most SBOM and licence-scanning tooling, identify a licence by
matching a file's text against known templates. That one line was enough to
break the match, so the GitHub API reported `NOASSERTION`, the repository badge
read "Other", and automated scanners saw an unidentifiable licence.

The copyright line lives in [NOTICE](NOTICE), and `LICENSE` is byte-identical
to the canonical licence text.

### 2. Earlier licences, and the 2026-11-28 switch to Apache-2.0

| Period | Licence | Copyright holder |
|---|---|---|
| 2023 – 2024 | MIT | Capsize Games |
| 2025 (part) | Apache-2.0 | Capsize Games |
| 2026-09 – 2026-11 | GPL-3.0-only | Capsize LLC |
| 2026-11-28 – | Apache-2.0 | Capsize LLC |

The project owner decided on 2026-11-27/28 to return to Apache-2.0, a less
restrictive licence, to make adoption and contribution easier for engineers
whose employers restrict GPL-licensed code.

**Rights in earlier code are unaffected.** Licence grants are irrevocable and
forward-only: if you forked or vendored AI Runner under MIT, Apache-2.0, or
GPL-3.0, you may continue to use the code as it stood at that time under those
terms. This relicensing applies going forward, from the commit that changed
`LICENSE`, not retroactively.

**Basis for the switch.** Almost all code on the current tree is Capsize-owned
or was contributed under permissive licences, which permit relicensing. Four
commits by two external contributors were merged while GPL-3.0-only was in
effect (September–November 2026), and the project held no CLA from them. To
avoid relicensing anyone else's creative work without their agreement, the
creative parts of those contributions — three test files — were replaced with
maintainer-authored equivalents before the switch; the remaining parts are
single functional lines (an import and parameter forwarding) whose behaviour
is unchanged. Both contributors were also notified in a public relicensing
issue and invited to consent or object; if either objects, Capsize will
address their contribution specifically. If you are unsure which terms apply
to a particular commit, the licence in effect is whatever `LICENSE` contained
at that commit.
