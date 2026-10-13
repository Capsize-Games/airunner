# Counsel-support memo: US-law grounding for the safety-notices delta — DRAFT, NOT LEGAL ADVICE

> DRAFT FOR COUNSEL REVIEW. Research support for
> `safety-notices-delta-draft.md` D1–D5, drawn from the
> workstation US-law corpus (`~/Projects/usds`, FTS index:
> 60,458 usc + 48,672 state + 1,001 ecfr + 24,526 fr records;
> corpus current to ~2026-10-11). Every citation below was
> spot-checked against the index. This memo is not legal
> advice, states no conclusion, and must not ship. Bracketed
> COUNSEL items are unresolved. Issues: L05 (#2132), L06
> (#2135), Q06 (#2128).

- Document:
  `release-planning/linux-v1/legal/usds-counsel-support-memo.md`
- Version: 0.1 (2026-10-13)
- Supports: `safety-notices-delta-draft.md` v0.1 (D1–D5)

## D1 — on-device processing / no-copy claims

- 15 USC 45(a)(1): unfair or deceptive acts or practices are
  unlawful — this is the statute our offline/no-copy wording
  will be judged under. Warn: do not overstate "keeps no
  copy" beyond what the logging code provably does.
- 15 USC 45(a)(2): FTC enforcement basis (banks, carriers
  carved out; we are neither).
- 15 USC 6501(4), (8), (9): COPPA definitions of personal
  information, verifiable consent, disclosure (disclosure
  excludes internal-operations handoffs).
- 15 USC 6502(a)(1), (b)(1)(A): notice plus verifiable
  parental consent before collection from a child.
- 16 CFR 312.2: "collection" includes passive tracking;
  internal-operations use must not enable contact or
  profiling. [COUNSEL: reviewer log fields — do any count
  as personal information?]
- 16 CFR 312.5(a), (c)(6)–(7): consent-first posture with
  narrow security / identifier-only exceptions.
- 16 CFR 312.8: written security program required of
  operators — template for our posture statement.
- 16 CFR 312.10: retain personal information only as long
  as necessary + written deletion policy — our D1 stance
  will be read against this floor.

## D2 — model-download disclosure as the collection point

- 15 USC 6501(1): child means under 13.
- 15 USC 6501(2): operator means a commercial online
  service — a fully-offline app sits outside; the D2
  downloads are the point where online duties attach.
- 15 USC 6502(b)(1): duties trigger on online collection.
- 15 USC 6502(b)(2): narrow one-time-contact and safety
  exceptions — the only no-consent analogues in reach.

## D3 — filter disclosure and no-guarantee wording

- 47 USC 230(c)(1): publisher shield covering both
  over- and under-blocking.
- 47 USC 230(c)(2)(A)–(B): good-faith restriction of
  otherwise-objectionable matter plus access-tool
  provision — core support for mandatory + optional
  filters; 230(f)(2), (4) fits a local filter as access
  software.
- 47 USC 230(d): parental-control availability notice —
  closest disclosure analogue for the optional filter.
- 47 USC 230(e)(2)–(3): intellectual-property and state-law
  bounds — [COUNSEL: map to territory remedies].
- 17 USC 512(i)(1): noticed repeat-infringer-style policy
  as precedent for publishing the filter policy.
- 17 USC 512(m): no duty to monitor — supports stating
  best-effort rather than guaranteeing outcomes.
- 17 USC 512(c)(1), (c)(3): notice-element template for a
  report channel (analogy only).
- 17 USC 512(g)(1)–(3): notice + counter-notification +
  putback as template for appeal/restore (analogy only).
- 17 USC 512(f): warns against knowing misrepresentation
  in notices.
- 15 USC 45(a)(1) again: overpromising efficacy is itself
  a UDAP risk — the disclaimer must avoid becoming the
  deceptive claim.
- 15 USC 2301, 2308 (Magnuson-Moss): keep best-effort as a
  statement of fact, not a warranty disclaimer.
  [COUNSEL: reach to GPL software unconfirmed; ch. 50
  tangible-product fit unconfirmed.]

## D4 — offline/remote statement and state stacking

- 15 USC 6502(c), 6505: COPPA violations are UDAP,
  FTC-enforced.
- 15 USC 6502(d): only inconsistent state law is
  preempted — so FL Rule 2-43.003 (Permanent Deletion)
  can stack on top. [Pull current rule text from
  flrules.org before reliance — corpus holds the index
  entry only.]
- 15 USC 6504: state-attorney-general actions preserved.
- Mini-FTC-act anchors: NM 12.2.2 (NMSA 57-12-1),
  CT 42-110b (regulations guaranteed).

## D5 — consent records and acknowledgment/consent split

- 15 USC 7001(c)(1) (E-SIGN): prior consent plus clear
  disclosures, hardware/software requirements, and
  demonstrated access — checklist for first-run
  acceptance.
- 15 USC 7001(b)(2): no one must accept electronic
  records — supports recording license acknowledgment
  separately from optional data-processing consent.
- 15 USC 6502(b)(1)(A)(ii) + 16 CFR 312.5: verifiable
  consent before collection or material change.
- 15 USC 7001(c)(4): withdrawal is prospective within a
  reasonable time — maps to D5 "effect on subsequent
  runs."
- 15 USC 7001(d)(1): electronic acceptance suffices where
  accurate, accessible, and reproducible.
- 16 CFR 312.10 again: written retention + deletion floor
  for any records kept.

## Absent from the corpus (do not cite what is not there)

- No case law and no FTC guidance documents (Deception
  Policy Statement, .com Disclosures); FR COPPA queries
  came back empty.
- No California source: no CCPA/CPRA regulations, no
  age-appropriate-design code.
- No Utah Accountability Act source.
- No state UDAP statute at section level (FL 2-2 repealed
  1997; NC 02E repealed 1981).
- Unverified tails: FL 2-43.001–.003 bodies, 6504/6505
  full text, 7001(e) tail; 312 pinpoints at chapter-blob
  level only.

## Open questions for counsel (unchanged from delta draft)

1. COPPA child-directed vs. actual-knowledge standard for
   a general-audience desktop app.
2. Whether any reviewer log field counts as personal
   information per territory.
3. Magnuson-Moss reach and the D3 interplay with section
   10 consumer-remedy terms.
4. Filter-efficacy disclaimer doctrine (needs case law /
   Deception Policy outside this corpus).
5. State UDAP survey + CCPA/AADC/Utah follow-up offered
   once a California/Utah source is available.
