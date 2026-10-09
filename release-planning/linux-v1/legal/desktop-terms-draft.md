# AI Runner Desktop terms -- DRAFT FOR COUNSEL REVIEW

> DRAFT FOR COUNSEL REVIEW. This is a working draft grounded in
> the L01 evidence inventory and the P11 license inventory. It is
> not legal advice, not effective terms, and must not ship with
> the product until qualified counsel and the owner approve it.
> Bracketed OWNER and COUNSEL items below are unresolved.

- Document: `release-planning/linux-v1/legal/desktop-terms-draft.md`
- Version: 0.1 (2026-10-09)
- Issues: L03 (https://github.com/Capsize-Games/airunner/issues/2127),
  grounded in L01 (#2121) and P11 (#2113,
  `release-planning/linux-v1/licenses.md`)
- Replaces as a draft: `.../setup_wizard/user_agreement/user_agreement_text.md`
  (2025-11-30). Key corrections versus that text: the
  contradictory revocable/nontransferable "license grant" is
  removed (section 1); the unsupported automatic-reporting
  claim is removed (section 7); the broken incorporation of a
  README section that does not exist is removed (section 8);
  no blanket no-refund or rights-waiver language (section 10).
- Seller: Capsize LLC, a Colorado limited liability company.
  [OWNER: confirm entity, address, and contact channel.]

---

# AI Runner Desktop terms

**Updated: [UNSET -- set on counsel approval]**

By installing or using AI Runner Desktop (the "Software"),
buying an official copy, or using Capsize support, you agree
to these terms and to the privacy policy. If you do not
agree, do not install or use the Software. NOTHING HERE
LIMITS YOUR RIGHTS UNDER THE GNU GENERAL PUBLIC LICENSE:
where these terms and the GPL disagree about the Software
itself, the GPL controls.

## 1. The Software and your GPL rights

The Software is free software under the GNU General Public
License v3.0 only (`LICENSE`; copyright Capsize LLC, see
`NOTICE`; history in `RELICENSING.md`). You may run, study,
share, and modify it under the GPL, with no further
restrictions from us on those freedoms. We do not grant a
separate revocable, non-transferable license to the Software
itself: your rights to the code come from the GPL and cannot
be taken back by these terms.

Paid distribution carries a written corresponding-source
offer as the GPL requires. [OWNER/COUNSEL: the offer text is
release BLOCKER B-8 in `licenses.md` -- approve it and state
where buyers find it.]

## 2. What you pay for

Money buys convenience, not permission: an official
installer or package, timely official builds, and whatever
support is described in section 4. It does not buy the
underlying GPL freedoms, which are already yours, and the
Software contains no license keys, activation, usage
tracking, or copy protection. [OWNER: confirm the price,
what the package includes, and any media/shipping terms.]

## 3. Updates

[OWNER: confirm the update promise. Suggested posture, to be
confirmed:] Official release builds issued during the
support window are included with purchase at no extra
charge. The application does not update itself: system
packages update through your package manager, and any
future in-app update check will ask first (the updater is
designed as explicit opt-in and stays off while offline
mode is on). We do not promise release dates, perpetual
updates, or that any particular feature or model will keep
working with future third-party services.

## 4. Support

[OWNER: define the support offering -- channels, hours,
response targets, what is covered (installation, defects)
and what is not (model tuning, third-party services,
custom development), duration, and any paid tiers. Do not
ship this section with placeholders.] Suggested limits to
confirm: support covers the official build on supported
systems; it does not cover modified copies beyond pointing
out the difference; and no outcome or deadline is promised
unless a paid plan states one. Community channels, if any,
are best-effort and not covered by response targets.

## 5. Trademarks and branding

"AI Runner", the AI Runner logo, and Capsize marks belong to
Capsize LLC. The GPL gives you rights to the code, not to
the marks: if you redistribute modified copies, do not
present them as official Capsize builds and remove or
replace branding that would confuse users about the source.
[COUNSEL: confirm the rebrand/confusion rule and whether a
trademark policy page is needed.]

## 6. Third-party models, data, and services

The Software runs models and data from others (Hugging Face,
CivitAI, Kiwix libraries, and any external AI provider you
configure). Your use of each is governed by ITS license and
terms, not by these terms: check them before commercial or
redistributive use. A downloader or preset inside the
Software is not an endorsement, and we are not responsible
for what third-party models do, contain, or generate. Model
files are downloaded after installation, are never part of
the bundle, and upstream projects can change or remove
them. [COUNSEL: confirm the model-license responsibility
allocation, including the unpinned-artifact caveats in
`licenses.md` BLOCKERs B-2/B-3, before release.]

## 7. Acceptable use

Use the Software lawfully and do not use it to:

- break any applicable law, including export-control and
  sanctions law, or to commit fraud or financial crime;
- create or share sexual content involving children in any
  form, including AI-generated material, or content that
  sexualizes, grooms, or endangers children;
- create intimate or sexual imagery of real people without
  their explicit consent, or content facilitating human
  trafficking or sexual exploitation;
- harass, threaten, stalk, or intimidate anyone;
- glorify or incite violence, terrorism, or violent
  extremism, or instruct wrongdoing with weapons,
  explosives, or chemical, biological, or cyber weapons;
- depict or encourage animal cruelty;
- impersonate others, forge documents or credentials, or
  deliberately make and spread harmful disinformation;
- develop or spread malware, phishing, or intrusion tools;
- discriminate against or dehumanize people based on
  protected characteristics;
- process other people's personal or biometric data without
  a lawful basis, or surveil people with the Software;
- use the Software as medical, legal, financial, or mental
  health advice, or in safety-critical or high-risk systems
  where failure could kill, injure, or cause severe harm,
  or to make unsupervised decisions significantly
  affecting people's rights, employment, credit, or access
  to essential services.

Because the Software runs locally on your machine, Capsize
cannot monitor or automatically report your use: you are
responsible for complying with this section. Breach may
lead us to refuse or end PAID services and support where
the law allows; it does not revoke your GPL rights to the
Software itself. [COUNSEL: confirm the remedy wording --
refusal of paid services only -- and whether any reporting
duty (for example, CSAM knowledge obtained through support
channels) needs stating.]

## 8. AI limitations and content notices

- Generated content can be wrong, fabricated, biased,
  offensive, or infringing. Verify before relying on it.
- Image, voice, and text generation can make synthetic
  media. Do not use it to deceive, defame, or violate
  others' rights, including intellectual-property rights.
- Nothing the Software generates is professional advice.
  Consult qualified professionals for medical, legal,
  financial, or safety decisions.
- The built-in content-safety layer is best-effort
  defense-in-depth, not a guarantee: the shipped policy
  data starts empty and is provisioned at release time,
  optional layers stay off unless enabled, and anything
  can be enabled, disabled, or removed in a modified copy.
  The prohibitions in section 7 apply regardless of what
  any filter catches. (See `README.md` "Content Safety"
  and `SECURITY.md`.)
- If you use the Software for decisions with legal or
  similarly significant effects on people (hiring, credit,
  housing, insurance), you may be the deployer of a
  regulated AI system with duties of your own, including
  under the Colorado AI Act for Colorado uses. That
  compliance is yours. [COUNSEL: confirm this allocation
  and whether EU AI Act deployer wording is needed for
  worldwide sales.]
- Private policy vocabulary and signing material used to
  build official releases are Capsize confidential
  information, are never published, and are not part of
  the GPL source offer for the application. [COUNSEL:
  confirm this carve-out is stated correctly and
  consistently with the source offer in section 1.]

## 9. Age and content warning

You must be 18 or older (or the age of majority where you
live) to use the Software. Generated content is
unpredictable and may include sexual, nude, violent, or
otherwise offensive material: use discretion and your own
risk. [COUNSEL: confirm the age line and whether app-store
or territory-specific content-rating wording is required.]

## 10. Consumer rights and refunds

[OWNER: state the refund rule -- window, conditions, who
handles it (Capsize or the storefront), and how digital
delivery affects it in each sales territory. Do not ship a
blanket "no refunds" line.] Nothing here waives consumer
rights the law in your territory gives you and does not let
you sign away: where the law guarantees remedies for
faulty digital goods, those remedies apply. [COUNSEL:
supply the per-territory treatment for worldwide sales,
including EU/UK digital-content and withdrawal rules and
any US state requirements.]

## 11. Privacy

How the Software, purchases, and support handle information
is described in the privacy policy, which forms part of
these terms. Read it before buying or contacting support.

## 12. Warranty and liability

The Software's warranty and liability position follows the
GPL: the program is provided WITHOUT WARRANTY (GPL section
15) and in no event will the copyright holders be liable
beyond what GPL section 16 allows, TO THE FULLEST EXTENT
THE LAW ALLOWS. Where the law in your territory implies
warranties or forbids excluding or limiting certain
damages, our warranties are limited and our liability is
limited to the maximum extent the law permits, and nothing
here excludes liability the law does not let us exclude
(such as for fraud or willful misconduct). [COUNSEL:
confirm the savings clause covers paid-installer and
support liability in every sales territory, and whether a
monetary cap (for example, the amount paid) should be
stated for the paid elements.]

## 13. Indemnification

[COUNSEL: the prior draft's broad indemnity (all claims
from any use or generated content, including attorney's
fees) is aggressive for worldwide consumer sales next to
GPL freedoms. Confirm whether to keep a narrowed version
(for example, misuse breaching section 7, or business-use
indemnity only), or drop it. Do not ship the old broad
clause unreviewed.]

## 14. Governing law and disputes

[COUNSEL: the prior draft chose Colorado law with exclusive
Colorado courts. Confirm this survives for worldwide sales,
or supply consumer-friendly alternatives (for example,
buyer's-home-court options where mandatory law requires
them) and state whether arbitration is wanted. Do not ship
exclusive-venue language that mandatory consumer law would
override without saying so.]

## 15. Changes, severability, entire agreement, contact

We may change these terms; the date above will show the
latest version and [OWNER: state how buyers are told --
email, website, in-app notice, or a combination]. Continued
use of paid services after a change takes effect means you
accept it; the GPL terms for the Software itself change
only as the GPL provides. If any part of these terms is
unenforceable, the rest stands. These terms plus the
privacy policy are the whole agreement about the official
offering. Questions: [OWNER: confirm address -- current
text uses `contact@capsizegames.com`].

---

## Unresolved decisions (must clear before these ship)

| # | Decision | Owner |
|---|---|---|
| D1 | Corresponding-source offer text and location (BLOCKER B-8) | Owner + counsel |
| D2 | Price, package contents, delivery, support scope and window | Owner |
| D3 | Refund rule per territory; consumer-rights savings (section 10) | Owner + counsel |
| D4 | Indemnity: narrow, business-only, or drop (section 13) | Counsel |
| D5 | Governing law, venue, arbitration posture (section 14) | Counsel |
| D6 | Trademark/redistribution-branding rule (section 5) | Counsel |
| D7 | Model-license allocation confirmation incl. B-2/B-3 (section 6) | Counsel |
| D8 | Remedy wording and any reporting-duty statement (section 7) | Counsel |
| D9 | Liability cap for paid elements (section 12) | Counsel |
| D10 | Policy-data confidentiality carve-out vs source offer (section 8) | Counsel |
| D11 | Age/content-rating wording per territory (section 9) | Counsel |
| D12 | Change-notification channel and contact address (section 15) | Owner |

## Reviewer fields

- Owner reviewer: PENDING -- Owner date (UTC): PENDING
- Counsel reviewer: PENDING -- Counsel date (UTC): PENDING
- Approved version and effective date: PENDING
- Acceptance: PENDING (issue #2127 stays open until
  counsel-approved text is staged for release; L05 tracks
  the human acceptance gate)
