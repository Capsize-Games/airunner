# Egress coverage ledger (Linux v1)

Issue: https://github.com/Capsize-Games/airunner/issues/2091 (O01). Parent: https://github.com/Capsize-Games/airunner/issues/2083.

This enumerates every outbound (real-internet, non-loopback) network call site found in this checkout, and states whether it is now covered by the new offline-mode gate added in `services/src/airunner_services/url_safety.py` (`validate_url_for_fetch()` denies any call when `AIRUNNER_OFFLINE_MODE` is true, the new default). Per the ticket's own instruction, this is an enumeration of what is and is not covered — it is not a claim of full coverage, and most rows below are **not** covered yet.

Loopback-only traffic is out of scope and excluded: `GuiDaemonClient`'s calls to the daemon's own `127.0.0.1` API, all `runtimes/sidecar_*_client.py`/`sidecar_*_launcher.py` subprocess IPC, `eval/client.py`/`eval/fixtures.py`'s default `http://localhost:8188`, and Ollama's default `http://localhost:11434` (each is separately gated by the existing loopback-token/API-key policy from S01/S02, an already-authenticated code path this ticket does not change).

## What changed in this ticket

- `shared/airunner_common/settings.py`: new `AIRUNNER_OFFLINE_MODE` (default `True`).
- `services/src/airunner_services/url_safety.py`: `validate_url_for_fetch()` now denies with `OfflineModeBlocked` before any DNS/network-adjacent work when offline mode is on; SSRF checks (`SSRFBlocked`) still run afterward once online. Also fixed a latent bug found while adding this: `SSRFBlocked`/`OfflineModeBlocked` were `@dataclass(frozen=True)` exceptions, which crash with `FrozenInstanceError` instead of propagating cleanly when raised through 2+ nested generator-based context managers (CPython's exception machinery assigns `__traceback__` onto the instance as it unwinds). Removed `frozen=True` from both.
- Three pre-existing call sites caught only `SSRFBlocked` around `validate_url_for_fetch()`, which would have let the new sibling `OfflineModeBlocked` propagate unhandled instead of being skipped gracefully: `tools/scrapy/spiders/llm_guided_spider.py`, `llm/tools/intelligent_crawl_tool.py`, `tools/web_content_extractor.py` (4 sites). All now catch `(SSRFBlocked, OfflineModeBlocked)`.
- `src/airunner/url_safety.py` (compat re-export shim, issue #2048) re-exports the two new symbols.

## Covered — routes through `validate_url_for_fetch` / `safe_fetch_url` / `safe_fetch_bytes`

| Site | Mechanism | What it does |
|---|---|---|
| `services/src/airunner_services/tools/web_content_extractor.py` (`_safe_fetch_html`) | `safe_fetch_url` | Fetches a web page's HTML for scraping/summarization (`scrape_website` tool, search-result content) |
| `services/src/airunner_services/kiwix_api.py` (`KiwixAPI.list_zim_files`, services-side) | `safe_fetch_url` | Fetches the Kiwix ZIM-library Atom catalog feed |
| `src/airunner/components/documents/gui/widgets/kiwix_widget.py` (`_add_illustration_to_layout`) | `safe_fetch_bytes` | Downloads a Kiwix catalog entry's thumbnail illustration |
| `src/airunner/components/art/gui/widgets/canvas/mixins/canvas_dragdrop_mixin.py` | `safe_fetch_bytes` | Downloads an image dragged/dropped onto the art canvas from a URL |
| `services/src/airunner_services/downloads/civitai.py` (`_get_streaming_response`) | `requests.get` + `validate_url_for_fetch` per redirect hop | Downloads the actual CivitAI model file |
| `services/src/airunner_services/api/routes/downloads.py` (`fetch_civitai_image_route`) | `safe_fetch_bytes` | Serves a CivitAI preview image to the GUI |
| `services/src/airunner_services/downloads/job_service.py` (`start_url_download`) | `validate_url_for_fetch` | Validates a user-supplied generic download URL before the job runs |
| `services/src/airunner_services/tools/scrapy/spiders/llm_guided_spider.py` (`parse`) | `validate_url_for_fetch` (pre-check only — see caveat) | Validates each candidate follow-link before yielding a `scrapy.Request` |
| `services/src/airunner_services/llm/tools/intelligent_crawl_tool.py` (`intelligent_crawl`) | `validate_url_for_fetch` (pre-check only — see caveat) | Validates the crawl's `start_url` before launching the Scrapy `CrawlerProcess` |

**Caveat on the two Scrapy sites**: `validate_url_for_fetch` gates whether the crawl is allowed to *start*/follow a *specific link*, so offline mode does block it. But Scrapy's actual page-fetch transport is its own Twisted-based downloader (`CrawlerProcess`), which never goes through `requests`/`safe_fetch_url` — so `safe_fetch_url`'s redirect-hop revalidation, byte cap, and timeout enforcement do not apply to the real network I/O once a crawl is running, only the initial per-link admission check.

## Not covered — direct network calls bypassing `url_safety`

| Site | Mechanism | What it does |
|---|---|---|
| `services/src/airunner_services/downloads/civitai.py` (`fetch_model_info`, `search_models`) | `requests.get` | CivitAI model metadata/search API |
| `services/src/airunner_services/downloads/job_service.py` (`_run_civitai_model_job` → `fetch_model_info_for_url`) | (calls the above) | Production daemon download-job path hitting the uncovered CivitAI metadata call |
| `services/src/airunner_services/bin/airunner_civitai_download.py` | `requests.get` | Standalone CLI script; no `url_safety` import at all |
| `services/src/airunner_services/llm/utils/model_downloader.py` (`HuggingFaceDownloader.get_model_files`, `download_file`) | `requests.get` | Lists/downloads HuggingFace repo files |
| `src/airunner/components/llm/utils/model_downloader.py` | `requests.get` | GUI-side duplicate of the above, same gap |
| `services/src/airunner_services/downloads/huggingface_download_worker.py` (`_download_and_extract_zip`, `_download_gguf_model`, `_download_file`) | `requests.head` / `requests.get` (streamed) | The actual curated HuggingFace model/GGUF/zip download path (see D01) |
| `src/airunner/components/application/workers/download_worker.py` (`get_size`, `_execute_download`) | `requests.head` / `requests.get` | GUI-side generic download worker |
| `src/airunner/components/documents/kiwix_api.py` (GUI-side copy, distinct file from the covered services-side one) | `requests.get` | Fetches the Kiwix catalog feed directly |
| `src/airunner/components/documents/gui/widgets/kiwix_widget.py` (inner `DownloadWorker.run`) | `requests.get` (streamed) | Downloads the actual `.zim` file (the illustration fetch in this same widget *is* covered — the ZIM file itself is not) |
| `services/src/airunner_services/tools/search_providers/duckduckgo_provider.py` | `ddgs.DDGS` (fallback `duckduckgo_search.DDGS`) | DuckDuckGo web/news search — the library makes its own HTTP requests internally |
| `services/src/airunner_services/tools/search_providers/arxiv_provider.py` | `aiohttp.ClientSession` | Queries the arXiv API |
| `services/src/airunner_services/llm/adapters/mixins/generation_vision_image_loading.py` (`image_from_remote_url`) | `urllib.request.urlopen` | Downloads a remote image URL supplied for vision-model input |
| `services/src/airunner_services/llm/managers/agent/weather_mixin.py` (`get_weather`) | `openmeteo_requests.Client` | Open-Meteo weather API; gated only by the existing `is_openmeteo_allowed()` privacy flag |
| `services/src/airunner_services/llm/adapters/chat_model_factory_model_builders.py` (`create_openrouter_model`, `create_openai_model`) | `langchain_openai.ChatOpenAI` (httpx-based) | OpenRouter / real OpenAI chat completions; each gated only by its own `is_*_allowed()` privacy flag |

## Not covered, arguably out of scope (eval/test tooling)

| Site | Mechanism | What it does |
|---|---|---|
| `services/src/airunner_services/eval/mixins/download_mixin.py` | `requests.get` | Downloads eval benchmark datasets from `huggingface.co/datasets/...` |
| `services/src/airunner_services/eval/judge_providers.py` | `requests.post` | Calls Groq or OpenRouter as an LLM-judge backend for eval scoring |

## Uncertain / needs a human decision

- `create_ollama_model` defaults to `http://localhost:11434` but `base_url` is caller-configurable, so a remote Ollama endpoint is possible and would bypass `url_safety` entirely if one is ever wired in. Currently excluded above as loopback-by-default; flagging in case a remote-Ollama path exists that this pass didn't find.
- `eval/client.py`'s `AIRunnerClient` similarly defaults to loopback but accepts a `base_url` override.

## What this means for the offline-by-default policy

Wiring the gate into `url_safety.py` — the module copilot-instructions.md already designates as "the existing URL safety layer" for new fetch paths — was deliberately chosen as **one** central, low-risk integration point per the ticket's own instruction ("add a first integration at the central fetch/provider boundary... break additional call-site wiring into follow-up tickets"). It fully covers Kiwix browsing, the CivitAI preview-image proxy, the generic user-URL download route, web content extraction/scraping, and (for admission purposes) the two Scrapy crawl entry points.

It does **not** yet cover the actual curated model-download pipeline (HuggingFace, CivitAI file download, the GUI-side generic download worker), DuckDuckGo/arXiv search, remote vision-image loading, weather, or the OpenRouter/OpenAI chat providers — every row in "Not covered" above would still make its outbound call today even with `AIRUNNER_OFFLINE_MODE=1`. Wiring each of those through `validate_url_for_fetch` (or an equivalent gate for the non-`requests`-based ones: `ddgs`, `aiohttp`, `langchain_openai`, `openmeteo_requests`) is real, separate, per-call-site work — each with its own blast radius and testing needs — and is exactly what this ledger exists to hand off rather than paper over with a false "fully covered" claim.

## Validation

Every call site above was located by grepping for `requests.get(`, `requests.post(`, `requests.head(`, `requests.Session(`, `aiohttp`, `httpx.`, `urllib.request`, `ddgs`/`DDGS`/`duckduckgo`, and Scrapy/Crawler usage across `services/src/airunner_services/` and `src/airunner/`, then reading each hit's surrounding context to determine whether it already routes through `url_safety`. No runtime launch, model load, or real network access was performed to produce this document.
