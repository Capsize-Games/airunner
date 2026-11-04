# Linux RAG dependency review

Status: static review is in progress. No package in this batch was installed, imported, built, or activated by this review. Native libzim provenance and its source-build path remain unresolved.

## Artifact correspondence

All nine selected wheels passed RECORD hash/size checks. The Python files in each pure Python wheel match the corresponding hash-verified source distribution byte-for-byte. libzim contains a compiled extension rather than Python runtime source; RECORD integrity does not establish its native source provenance.

| Distribution | Matching runtime Python files | Wheel SHA-256 |
| --- | ---: | --- |
| `ebooklib==0.19` | 9 | `a790e280e1d5ef105e350e34cc88b83c9c987fa6bab8a63a7543410c313cfa31` |
| `langchain-huggingface==1.2.2` | 14 | `f94944b0c0d5afc687568d426c87ed5236907464c41e72108ed76eee1a690f6d` |
| `langchain-text-splitters==1.1.2` | 13 | `a2de0d799ff31886429fd6e2e0032df275b60ec817c19059a7b46181cc1c2f10` |
| `libzim==3.7.0` | 0 | `6abe60b6542f95f920d713ef468382942f64787adac07e9b66bc76be0b97f48b` |
| `loguru==0.7.3` | 19 | `31a33c10c8e1e10422bfd431aeb5d351c7cf7fa671e3c4df004162264b28220c` |
| `mobi==0.4.1` | 22 | `5490ea1d8e62c4d94352b6ba8eb117b9f9e5df2a1e8b38687c11d1f390cf86e5` |
| `pypdf==6.21.4` | 59 | `33e4fb41ca352810eb4e9838aa0d82d6888a5f8bf682f43e99cce5faa666255c` |
| `six==1.17.0` | 1 | `4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274` |
| `standard-imghdr==3.13.0` | 1 | `30a1bff5465605bb496f842a6ac3cc1f2131bf3025b0da28d4877d6d4b7cc8e9` |

## Source retention

The six independent canonical repositories below are preserved in owner-controlled private maintenance repositories with Actions disabled. Exact selected branches were checked against the canonical tag commits. No automatic upstream synchronization is configured. LangChain integrations and standard-imghdr use the separately retained shared LangChain and Python deadlib source copies.

| Source | Tag | Commit |
| --- | --- | --- |
| https://github.com/aerkalov/ebooklib.git | `v0.19` | `cf1d2144eb6862c09456bc16713c0e24a2a727e1` |
| https://github.com/openzim/python-libzim.git | `v3.7.0` | `b9182a2d4b61d605ba886b7730e30add538bc1ed` |
| https://github.com/Delgan/loguru.git | `0.7.3` | `ae3bfd1b85b6b4a3db535f69b975687c79498be4` |
| https://github.com/iscc/mobi.git | `v0.4.1` | `fe9ec39cf6558ed237953874cc4cb27768ea0e4c` |
| https://github.com/benjaminp/six.git | `1.17.0` | `ebd9b3af90247b8858d415a05e96e9ee61e48d07` |
| https://github.com/py-pdf/pypdf.git | `6.21.4` | `b2c3fa2ee689f582a0de256a45e30bd96c68f807` |

## Findings and retained scope

- **pypdf:** the old 6.19.0 candidate has 18 published denial-of-service advisories. The reviewed replacement is 6.21.4, with no vulnerabilities listed in its retrieved PyPI release metadata. Its release delta includes bounded cross-reference processing, EOF detection and clone-loop guards. The application dependency floor is being raised separately. The static runtime review found an explicit optional jbig2dec subprocess path using argument lists, generated temporary filenames and configured output limits; it does not use a shell. Actual parser resource-limit acceptance remains unrun.
- **EbookLib:** setup.py reads local README metadata and declares setuptools dependencies; it contains no custom download hook. Runtime URL references include URL parsing rather than automatic network access. An optional Tidy plugin launches a configured local executable. Its GNU Affero General Public License text is preserved in the source and wheel; distribution obligations must remain represented in the complete release notices.
- **LangChain integrations:** Hugging Face support includes explicit hosted endpoint clients as well as the local embedding adapter. The verified local E5 service path requires local files and disables remote code. The HTML splitter URL helper explicitly fetches caller-selected content through LangChain Core’s SSRF-safe client; the service document splitter uses local text. This is a review of these paths, not a claim that every optional integration is offline.
- **mobi, six and standard-imghdr:** build metadata uses the declared standard build backends; runtime wheel sources match the sdists. Six contains Python compatibility helpers including exec_ and module aliases; those are not evidence of hidden execution. The reviewed mobi source retains GPL-3.0-only and standard-imghdr retains its upstream license. Archive/parser robustness is separate from provenance and remains part of document acceptance.
- **Loguru:** standard flit metadata, no custom project install hook. The runtime source contains pickle support for its own exception/queue serialization. This does not authorize consuming attacker-controlled pickle messages or establish arbitrary logging-sink safety. MIT text is retained.
- **libzim:** the selected wheel hash and RECORD validate, but the source build hook retrieves native archive inputs without the required pinned artifact verification. Do not run that build hook. The exact native bundle and its bundled library source/license closure still need review before activation; a wheel hash alone does not satisfy that gate. Preserve ZIM support while resolving those inputs.

## Limits and next work

These are bounded static findings, not exhaustive source or runtime certification. The source and artifact evidence is retained with exact metadata snapshots, hashes and correspondence results. Additional native dependencies, parser denial-of-service limits, source/build fixes, license payload completeness and the final resolved dependency graph must be verified before the full ML release lock is activated. Reviewed origin-policy flags are covered by the owner’s standing exception; no geographic approval is pending.
