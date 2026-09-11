# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 6.x.x   | :white_check_mark: |
| < 6.0   | :x:                |

## Reporting a Vulnerability

Please report vulnerabilities through GitHub's private security advisories
(not the public issue tracker):

https://github.com/Capsize-Games/airunner/security/advisories/new

You can expect an initial response within 7 days. We will keep you updated on the status of your report and notify you of the outcome once the vulnerability has been addressed or declined.

## Content Safety

AI Runner includes a best-effort content-safety layer to reduce the risk of
prohibited content flowing through generation. It is defense-in-depth, not a
guarantee: the governing policy remains the prohibition set out in the
[User Agreement](src/airunner/components/downloader/gui/windows/setup_wizard/user_agreement/user_agreement_text.md).
Where the automated layer and the User Agreement disagree, the User Agreement
controls, and users remain responsible for how they use the software.

### Input gate

Prompts are checked against a hash-based policy-terms data set at the daemon
generation boundary, so the same gate applies to every entry point that
reaches generation: the GUI, the HTTP API, legacy paths, and the LLM image
tool. The matcher normalizes text (case, separators, diacritics, simple
obfuscation) and compares hashes only; it never stores or logs prompt
content. A match produces a single generic rejection message with no side
effects -- no model unload, no job creation, and no echo of the matched text.

### Optional semantic input layer

An optional, secondary semantic layer can ask the local language model to
classify a prompt as allowed or not, reusing the same guardrails mechanism the
chatbot already uses. It is **off by default** and is enabled only when
`AIRUNNER_CONTENT_SAFETY_SEMANTIC` is set to `1` / `true` / `yes`. It never
replaces the hash matcher or the output filter, which remain the primary
defenses; it is a best-effort second signal that can only add a block.

The hash matcher always runs first. A hash match blocks immediately and the
model is never consulted. Otherwise, when the layer is enabled and a judge is
registered, the model is asked to answer with a single explicit token, and only
an explicit negative answer blocks. If the layer is disabled, no judge is
registered, the call times out, errors, or returns an ambiguous answer, the
request is allowed and a content-free status is logged. Every model call has a
short timeout, so this optional layer can never hang generation. It adds no
database column or migration, and no prompt text is ever logged.

### Policy data

The repository ships the policy data set EMPTY. It is populated out of band by
[`scripts/build_policy_terms.py`](scripts/build_policy_terms.py), which reads a
plaintext term list and writes only lowercase hex SHA-256 digests. The
plaintext list must stay outside the repository -- for example under the
gitignored `tmp/` directory -- and must never be committed. When no policy data
is loaded, the input gate passes prompts through so the application stays
usable; the maintainer is responsible for generating and shipping the data set.

### Output filter

Generated images pass through an output safety filter when the user enables it.
The filter fails **closed**: if it is enabled but cannot render a verdict
because the checker model is unavailable (for example unloaded mid-session or
only partially loaded), or because the check raises, the batch is blacked out
and every image is flagged as blocked rather than released unchecked. This
behavior is shared by the SDXL and Z-Image generation paths.
