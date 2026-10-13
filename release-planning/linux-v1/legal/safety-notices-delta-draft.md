# Safety-notices delta — DRAFT FOR COUNSEL REVIEW

> DRAFT FOR COUNSEL REVIEW. Proposed insertions for the L02
> privacy draft and L03 terms draft, prepared from the S07
> selection (`../safety-evaluation.md`), the L01 evidence
> inventory (`../privacy-facts.md`), and the shipped safety
> seams. This file is not legal advice, not an effective
> notice, and must not ship until qualified counsel and the
> owner approve each item. Bracketed OWNER and COUNSEL items
> are unresolved. Issues: L05
> (https://github.com/Capsize-Games/airunner/issues/2132),
> L06 (https://github.com/Capsize-Games/airunner/issues/2135),
> Q06 (https://github.com/Capsize-Games/airunner/issues/2128).

- Document:
  `release-planning/linux-v1/legal/safety-notices-delta-draft.md`
- Version: 0.1 (2026-10-13)
- Targets: `privacy-policy-draft.md` v0.1, `desktop-terms-draft.md`
  v0.1. This file proposes text only; the target drafts are
  unchanged until counsel approves.

## D1. Privacy draft: on-device safety processing (new subsection)

Proposed anchor: after the "Privacy features" list in
`privacy-policy-draft.md`.

> Safety checks run on your device. The application screens
> generation requests and generated images locally before
> they run or are shown: text is checked against built-in
> policy data and, only if you or your administrator enable
> the optional layers, by on-device review models. Images
> you generate, or supply as inputs, are reviewed in memory
> by an on-device image reviewer before they are displayed,
> saved, or sent anywhere. These checks make no network
> connection, send nothing to us or to any third party, and
> keep no copy of your content: the logs record only that a
> check ran and its generic outcome, never your words or
> images. [OWNER: confirm the reviewer weight files are
> provisioned the same post-install way as other models and
> are never part of the bundle. COUNSEL: confirm this
> characterization, including whether any log field counts
> as personal data per territory.]

## D2. Privacy draft: model-download disclosure covers reviewer weights

Proposed anchor: extend the "Model downloads" bullet in the
"Optional online features" section.

> If the on-device safety reviewers are not yet on your
> machine, fetching them connects to the same model services
> above, which see which files you request. Once stored
> locally, the reviewers run fully offline as described in
> the safety-checks section.

## D3. Terms draft: safety-filter disclosure (new subsection)

Proposed anchor: after section 7 ("Acceptable use") in
`desktop-terms-draft.md`.

> Safety filters. The Software ships with mandatory
> content-safety checks that may refuse a request or
> withhold a generated image, and with an optional
> adult-content filter you can switch on. The checks run
> locally as described in the privacy policy. They are a
> best-effort aid, not a guarantee: they may refuse benign
> content or miss content you find objectionable, and their
> optional layers stay off unless explicitly enabled (see
> the release notes for the version you run). Nothing in
> this section limits your GPL rights to the Software
> itself. [COUNSEL: confirm the no-guarantee wording and
> its interplay with consumer-remedy terms in section 10.]

## D4. Offline/remote statement (Q06 evidence wording)

For the Q06 operator script and, once approved, the privacy
draft's "Privacy features" offline bullet:

> The safety evaluators are local-only once provisioned:
> they are loaded from the local model cache with network
> access refused at load time, so no prompt, image, or
> verdict leaves the machine through the safety path. The
> one exception is provisioning itself (D2 above), which is
> an explicit download, not inference. Consent toggles that
> gate remote features do not change this posture: the
> mandatory image check has no off switch by design, and
> the optional text layers default to off.
>
> Known enforcement gaps the statement must NOT paper over
> (L01 §3; do not promise otherwise until fixed): the
> services-side downloader paths that ignore consent/offline
> gates, the unscreened vision-model remote-image input
> (Q08 template G1), and the unsynchronized GUI/services
> consent stores. [OWNER: rule on each gap — fix or
> accepted risk — before counsel finalizes.]

## D5. Consent records (L06 acceptance support)

> Accepted document versions are recorded locally (not sent
> anywhere): the installer/first-run flow writes the exact
> terms and privacy-policy versions the user accepted, with
> the acceptance date, to the local data directory, and the
> About/setup notices display those versions. Software
> license acknowledgment (GPL freedoms, no further
> restrictions) is recorded separately from any optional
> data-processing consent; declining an optional consent
> never blocks offline use, and optional consents can be
> withdrawn in Privacy Settings with effect on subsequent
> runs. No online account acceptance is required for
> offline use. [OWNER: confirm the exact record location
> and format; confirm the uninstaller's deletion list
> covers or explicitly excludes these records. COUNSEL:
> confirm the acknowledgment/consent split per territory.]

## Review checklist (all PENDING)

- [x] ACCEPTED by owner 2026-10-13: D1–D5 wording as
  drafted (not yet effective; still needs counsel review
  per item below before install).
- [ ] PENDING owner: entity/address/contact,
  reviewer-weight provisioning facts, gap rulings (D4).
- [ ] PENDING counsel: legal sufficiency of D1–D5, IP/territory
  wording, acknowledgment/consent split (D5), no-guarantee
  clause interplay (D3).
- [ ] PENDING release: install only the approved texts with
  matching digests/versions per L06; notices readable offline.
- Reviewer: ______ Date: ______
