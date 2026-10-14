# US-law grounding memo for the safety-notices delta — DRAFT, NOT LEGAL ADVICE

> OWNER-ACCEPTED RESEARCH SUPPORT (2026-10-13). Research support for
> `safety-notices-delta-draft.md` D1–D5, drawn from the
> workstation US-law corpus (`~/Projects/usds`, FTS index:
> 60,458 usc + 48,672 state + 1,001 ecfr + 24,526 fr records;
> corpus current to ~2026-10-11). Every citation below was
> spot-checked against the index. This memo is not legal
> advice, states no conclusion, and must not ship. No attorney
> review has been sought or is expected while the software is
> unreleased. Issues: L05 (#2132), L06 (#2135), Q06 (#2128).

- Document:
  `release-planning/linux-v1/legal/us-law-grounding-memo.md`
- Version: 0.2 (2026-10-14)
- Supports: `safety-notices-delta-draft.md` v0.1 (D1–D5)
- v0.2 re-check: corpus grown to 362,698 FTS records with a new
  `ftc` collection (usds commit `e645972`). Gaps 2–7 below
  re-verified closed except where noted; case law still absent.

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
  profiling. [OPEN LEGAL Q: reviewer log fields — do any count
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
  bounds — [OPEN LEGAL Q: map to territory remedies].
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
  [OPEN LEGAL Q: reach to GPL software unconfirmed; ch. 50
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

## Corpus gaps: resolved vs. still absent (re-checked 2026-10-14)

Resolved since v0.1 (usds commit `e645972`, 362,698 records):

- FTC guidance: CLOSED — new `ftc` collection holds all
  three (Deception Policy Statement, .com Disclosures
  2013, Unfairness Policy Statement). Provenance caveat:
  Deception pins search.ftc.gov; the other two pin Wayback
  snapshots. The D3 efficacy-disclaimer question can now be
  worked from these sources.
- FR COPPA bodies: CLOSED — 4,403/4,403 rulemaking bodies
  indexed; COPPA queries now hit body text.
- California statutes: CLOSED — Civ. Code §§1798.100+
  (CCPA) and §§1798.99.28–.99.31 (age-appropriate design)
  present. CCR (regs) still has an open gap row: no
  primary path, zero mirror rows.
- Utah Accountability Act: CLOSED — Title 13 Ch. 76
  present (§13-76-101 definitions, §13-76-201 app-store
  provider requirements, plus surrounding sections).
- State UDAP at section level: CLOSED — live FL
  §§501.204–.501.2042 present (repealed FL 2-2 / NC 02E
  remain dead ends, as before).
- FL Rules 2-43.001–.003: present at index level, but
  2-43.003 is short — still pull current text from
  flrules.org before reliance.
- 16 CFR 312 pinpoints: CLOSED — §§312.1–312.13 now
  indexed at section level (corpus current ~2026-10-01).
- 15 USC 6504/6505/7001 tails: present at index level
  (626/1,038/2,191 words).

Still absent — do not cite what is not there:

- Case law: no opinion corpus in the index (only
  incidental hits). Ingestion path is proven but not run
  (CourtListener bulk adapter benchmarked: 100k opinions
  to 1.34GB FTS; full ~8.3M universe estimated ~112GB).

## Open legal questions (for a future attorney if distribution starts) (unchanged from delta draft)

1. COPPA child-directed vs. actual-knowledge standard for
   a general-audience desktop app.
2. Whether any reviewer log field counts as personal
   information per territory.
3. Magnuson-Moss reach and the D3 interplay with section
   10 consumer-remedy terms.
4. Filter-efficacy disclaimer doctrine: now workable
   from the in-corpus FTC Deception and .com Disclosures
   statements (v0.2); case-law application still outside
   the corpus.
5. State UDAP survey + CCPA/AADC/Utah follow-up offered
   once a California/Utah source is available.
