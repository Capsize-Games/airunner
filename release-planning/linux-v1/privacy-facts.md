# Privacy data-flow inventory (Linux v1)

Issue: https://github.com/Capsize-Games/airunner/issues/2121 (L01).
Parent: https://github.com/Capsize-Games/airunner/issues/2083.
Status: working evidence record, not a legal clearance. A coding
agent cannot approve privacy representations; every item in section
8 needs an owner answer and counsel review before release.

Base: `0d551c7c8` (origin/master), inspected 2026-10-09 by static
code reading only. No GUI or model launch, no network access, no
paid API call, and no inspection of logs, secrets, or customer
records was performed. All paths below are repo-relative.

Companion ledger: `release-planning/linux-v1/egress-coverage-ledger.md`
(O01, issue #2091) enumerates outbound call sites. This inventory
builds on it with recipients, payloads, triggers, consent gates,
storage, retention, and deletion evidence.

## 1. Offline core: what provably stays on the machine

- Local inference runs in-process or in local sidecars
  (`llama-server`, `whisper-server` staged by
  `packaging/linux/stage-sidecars.sh`; torch/transformers/diffusers
  in the bundle). No inference call leaves the machine unless an
  external provider from section 2 is configured.
- The GUI talks to the daemon over a loopback-only HTTP API
  (default `127.0.0.1:8188`,
  `services/src/airunner_services/runtimes/daemon_config.py`).
  Non-loopback clients are rejected with 401 and loopback
  requests need the per-user token
  (`services/src/airunner_services/api/server.py`,
  `authenticate_connection`). The token is a random 32-byte
  value stored mode `0600` at
  `<base>/config/loopback_token`
  (`services/src/airunner_services/api/loopback_token.py`).
  Escape hatches that change this posture: a user-edited
  `daemon.yaml` host/port (non-loopback clients are still
  rejected) and `AIRUNNER_INSECURE_NO_AUTH=1` (disables auth;
  documented only in code).
- Crash capture is local-only. `src/airunner/crash_handler.py`
  writes `gui.log` / `faulthandler.log` under `<base>/logs` and
  `export_diagnostics()` states it makes no network call; the
  user must manually share the exported file. There is no
  crash-upload endpoint.
- No telemetry, analytics, or error-reporting SDK exists in
  `src/` or `services/src/`. Greps for sentry, posthog,
  mixpanel, matomo, goatcounter, bugsnag, rollbar, segment,
  and amplitude return no production hits (the single
  `opentelemetry` mention in `src/airunner/main.py` only
  silences a transitive logger).
- ZIP-code to coordinates lookup is a local file read
  (`2024_Gaz_zcta_national.txt` under `<base>/map/`,
  `services/src/airunner_services/utils/location/get_lat_lon.py`).
  No geocoding request leaves the machine.
- Offline mode is the default: `AIRUNNER_OFFLINE_MODE` defaults
  to `"1"`
  (`debian/vendor/airunner_common/settings.py`). Services-side
  consent checks deny every external service while it is on
  (`services/src/airunner_services/downloads/policy.py`,
  `is_service_allowed`).

## 2. External flows: what leaves the machine

`<base>` is `AIRUNNER_BASE_PATH`, default
`~/.local/share/airunner`
(`debian/vendor/airunner_common/settings.py`).

| # | Feature | Destination | Data sent | Trigger and gate |
|---|---|---|---|---|
| F1 | Hugging Face model downloads and repo metadata | `https://huggingface.co` (`/api/models/...`, `/.../resolve/...`) | Requested repo/file paths, revision; IP and TLS metadata by transport; `Authorization: Bearer` only when the user stored an HF token (`huggingface/api_key` in `<base>/config/settings.ini`, plaintext) | User-initiated download. GUI paths check the QSettings `privacy/allow_huggingface` flag (default allow) at two sites (`worker_manager.py`, `download_models_dialog.py`). The services curated-download worker (`downloads/huggingface_download_worker.py`) checks NO consent or offline gate: it downloads even when disallowed or offline. |
| F2 | CivitAI model search, metadata, and file downloads | `https://civitai.com/api/v1` plus file hosts | Model queries/IDs, download requests; optional API key from `application_settings.civit_ai_api_key` (SQLite, plaintext) | User-initiated. GUI browser checks QSettings `privacy/allow_civitai` (default allow). Services-side file bytes are re-validated per redirect hop; the metadata/search API calls are NOT gated (`downloads/civitai.py`, per the O01 ledger). |
| F3 | Web and news search | DuckDuckGo via the `ddgs` library | Query text, IP, result-fetch metadata | `search_web` / `search_news` agent tools, gated by services-side `is_duckduckgo_allowed()` (default allow, offline-aware). Effective default is BLOCKED because offline mode ships on. |
| F4 | Page scraping and guided crawls | Whatever site the user or agent targets | HTTP(S) fetch of the target URL (IP visible to the site operator); optional crawl follows links via Scrapy | `scrape_website` routes through `safe_fetch_url` (offline + SSRF gates, no per-service consent flag). `intelligent_crawl` admission-checks the start URL only; the crawl transport itself is Scrapy's own downloader. |
| F5 | Weather prompt | `https://api.open-meteo.com/v1/forecast` | Latitude, longitude, unit/format parameters | Triple gate, all required: `privacy/allow_openmeteo` (default DENY), per-chatbot `use_weather_prompt`, and global `use_weather_prompt` (`weather_mixin.py`). Responses cached locally 1 hour at `<base>/text/other/cache/.requests_cache`. |
| F6 | OpenRouter chat | `https://openrouter.ai/api/v1` | Prompts, conversation context, model parameters, user API key | `create_openrouter_model` raises unless `is_openrouter_allowed()` (default allow, offline-aware). Provider key required; `use_openrouter` defaults False. |
| F7 | OpenAI chat | OpenAI API via langchain `ChatOpenAI` | Same classes as F6 | Same gating shape as F6; default model `gpt-4`; `use_openai` defaults False. |
| F8 | Ollama chat and embeddings | Default `http://localhost:11434` (loopback); `base_url` is caller-configurable | Prompts (remote only if a remote URL is configured) | NO consent or offline gate on any Ollama path. Whether the UI exposes a remote URL field is UNVERIFIED (see Q-code Q4). |
| F9 | Kiwix offline-library catalog and ZIM downloads | `https://browse.library.kiwix.org/catalog/v2/entries` plus ZIM hosts | Catalog queries, illustration and ZIM downloads | User-initiated in the documents UI. NO consent or offline gate on either the GUI or services copy of the client. |
| F10 | Canvas image drag-and-drop from URL | The dropped URL's host | HTTP(S) fetch of that URL | User drops a URL onto the canvas. Routed through `safe_fetch_bytes` (offline + SSRF gates). Consent is the drop action itself. |
| F11 | Vision-model remote image input | Caller-supplied URL host | HTTP(S) fetch via bare `urllib` | `generation_vision_inputs.py` passes an agent-supplied path/URL to `image_from_remote_url`. NO consent, offline, or SSRF gate. |
| F12 | In-app update check | NONE WIRED: `downloads/update_check.py` (P10) requires explicit opt-in plus online mode, but no production `UpdateTransport` exists in this checkout, so no manifest host is contacted. The legacy `latest_version_check` toggle (default True) has no network caller; `UpdateWindow` only redisplays the local version. | n/a (no live flow) | Future wiring must pick a manifest host and keep the opt-in plus offline refusal. |
| F13 | OS package installs and updates | `https://apt.airunner.art` (per `README.md`) | Standard apt metadata/package fetches (IP visible) | User runs `apt update` / `apt install airunner`. This is the only FIRST-PARTY server flow found. Server logging and retention are owner facts (Q1). |
| F14 | Bug reports | `https://github.com/Capsize-Games/airunner/issues/new` (`AIRUNNER_BUG_REPORT_LINK`) | Whatever the user types into the GitHub form, in their browser | User-initiated; the app does not file or pre-fill reports. |
| F15 | arXiv search provider | `https://export.arxiv.org/api/query` | Would send query text | DORMANT: `ArxivProvider` has no callers outside its own package. No live flow, but the code ships. |
| F16 | Eval LLM-judge backends | Groq or OpenRouter | Eval prompts and outputs | Eval tooling only (`eval/judge_providers.py`), not a shipped runtime path. Disclose only if eval services are ever productized. |

NOT FOUND in code: any purchase, payment, license-key,
activation, entitlement, support-ticket, or account system. All
purchase/support data handling is off-app and needs owner facts
(section 8).

## 3. Consent architecture and enforcement gaps

Two parallel consent stores exist with no synchronization found:

- GUI store: Qt `QSettings` keys `privacy/allow_*`, written by
  the first-launch `PrivacyConsentDialog` and the Privacy
  Settings widget
  (`src/airunner/components/application/gui/dialogs/privacy_consent_dialog.py`,
  `src/airunner/components/settings/gui/widgets/privacy_settings/privacy_settings_widget.py`).
  Read only by the GUI-side HF/CivitAI gates. NOT offline-aware.
- Services store: INI file `<base>/config/settings.ini`, read
  by `downloads/policy.py` (offline-aware) for DDG, weather,
  OpenRouter, and OpenAI. No production caller of the
  services-side setters was found, and no GUI-to-daemon sync
  or API route for consent was found.

Consequences for any policy wording:

1. GUI toggles for DDG, weather, OpenRouter, and OpenAI do not
   observably reach the services-side enforcement. With
   default offline mode everything is still blocked, but once
   a user goes online (`AIRUNNER_OFFLINE_MODE=0`), services
   gates fall back to INI defaults and may ALLOW a service
   the user disabled in the GUI. Do not promise the GUI
   toggles are effective until a sync or single store lands.
2. The services HF worker (F1), CivitAI metadata API (F2),
   Kiwix (F9), Ollama incl. remote (F8), and vision-URL fetch
   (F11) have no gate at all. Do not promise they honor
   consent or offline mode.
3. Defaults are mixed: DDG/OpenRouter/OpenAI/HF/CivitAI
   default allow; weather defaults deny. Offline mode
   (default on) overrides the services-side allows only.

## 4. Local storage and retention

| Data | Location | Retention and deletion evidence |
|---|---|---|
| SQLite database (settings, conversations, documents, embeddings, companion facts, API keys) | `<base>/data/airunner.db` (`airunner.dev.db` in dev), overridable via `AIRUNNER_DATABASE_URL` | Kept indefinitely. No automatic expiry or vacuuming found. |
| Pre-migration DB snapshots | `<base>/data/backups/<stem>-<UTC stamp>.db` plus manifest, dir mode `0700` (`database/upgrade_backup.py`) | One snapshot per migration; NO automatic expiry or pruning found: they accumulate across upgrades. |
| Services settings incl. HF token | `<base>/config/settings.ini`, plaintext | Kept indefinitely; no encryption at rest. |
| GUI settings incl. consent flags | Qt `QSettings` (platform store) | Kept indefinitely; survives reinstall of the app package. |
| Provider API keys (OpenRouter/OpenAI/Ollama-adjacent) | `llm_generator_settings.api_key` (SQLite, plaintext) | Kept indefinitely; no encryption at rest. |
| HF/CivitAI keys (second copy) | `application_settings.hf_api_key_*`, `civit_ai_api_key` (SQLite, plaintext) | Same as above. |
| Daemon loopback token | `<base>/config/loopback_token`, mode `0600` | Persisted until deleted; recreates on next launch. |
| Application logs | `<base>/logs/airunner.log`, `gui.log`, `faulthandler.log` (append mode) | Unbounded growth for the main log: `FileHandler` append with NO rotation found. `LogHygieneFilter` redacts URLs, paths, and credential shapes; free-text content in exception messages is NOT guaranteed redacted (see `crash_handler.py` comments). Daemon file logging is optional and off by default (50 MB x 5 when enabled). |
| Diagnostics export | `<base>/logs/diagnostics_export.json` on demand | User-initiated file; allowlisted fields only (versions, platform, failure codes with message fingerprints, never message text). |
| Weather cache | `<base>/text/other/cache/.requests_cache` | 1-hour expiry, then refetched on use. |
| Models, media, ZIMs, RAG indexes, voice-model files | Under `<base>` (`models/`, `text/models/...`, image/document paths) or user-picked custom directories (`path_widget.py` offers a directory picker) | Kept indefinitely. Custom paths can sit OUTSIDE `<base>`. |
| Daemon config, heartbeat | Runtime layout config dir (`daemon.yaml`), heartbeat file | Kept indefinitely. |
| Location (ZIP, lat/long) | `user` table in SQLite | Kept indefinitely once entered. |
| Voice-clone reference | User file referenced by `openvoice_settings.reference_speaker_path` | Stays wherever the user keeps it; never uploaded by the app. |
| STT microphone audio | No at-rest recording path found: base64 audio arrives over the loopback API and is transcribed in memory | Transcripts enter the chat flow like typed text (INFERRED from the STT route shape; confirm before asserting). TTS output streams back as WAV; file export, if any, is user-initiated. |

## 5. Uninstall and deletion behavior

- Default uninstall PRESERVES all user data. `debian/` ships
  NO `postrm`, so `apt remove` leaves `<base>` intact. The
  tarball `packaging/linux/uninstall.sh` removes only
  installer-owned artifacts and states user data (models,
  media, database, settings, logs, backups) is untouched
  (`packaging/linux/UNINSTALL.md`).
- `--delete-data --yes` deletes an ALLOWLIST only:
  `airunner.db` plus SQLite sidecars, `settings.json`, and
  `service.log`. Surviving even explicit deletion: models,
  media, logs under `<base>/logs`, `<base>/data/backups/`,
  `<base>/config/settings.ini`, the loopback token, daemon
  config, weather cache, ZIMs, custom-path data, and Qt
  `QSettings`. Separately, `settings.json` is named by the
  script but no production code references it (the code uses
  `settings.ini`): confirm which file the bundle actually
  writes before promising either is removed.
- In-app deletion controls found: conversation DELETE
  endpoints (`api/routes/conversations.py`,
  `conversation_history_manager.delete_conversation`),
  companion-fact update/retract tools
  (`llm/tools/companion_memory_tools.py`). No whole-account
  wipe (there are no accounts) and no log/backup purge UI
  was found.

## 6. Sensitive data notes

- Voice characteristics (CPA-sensitive): processed locally by
  STT/TTS; no external voice API is wired. Voice-clone
  reference audio stays local. The bundled reference speaker
  `assets/reference_speakers/bobross.wav` has no rights
  record in this checkout (release BLOCKER B-10 in
  `release-planning/linux-v1/licenses.md`).
- Agent adaptation ("profiling" in the current policy):
  `companion_facts` table plus mood/summary cadence settings.
  Facts can be updated or retracted through agent tools; a
  one-click user-facing mood/memory reset control was NOT
  found (the current agreement asserts one exists: verify or
  reword).
- RAG documents and embeddings persist in the database and
  index paths until the user deletes them; scraped-page
  content persists under the webpages path.
- Location, API keys, and conversation transcripts persist
  indefinitely in plaintext SQLite/INI. Any "we protect your
  data" wording must not imply encryption at rest.

## 7. Existing policy promise audit

Each promise in `.../setup_wizard/user_agreement/privacy_policy.md`
(2025-11-30) mapped to evidence:

1. "Runs entirely on your local machine" / "We do not operate
   servers that collect, store, or process your personal
   data": CONTRADICTED unless narrowed. The app core is
   local, but `README.md` documents first-party
   `https://apt.airunner.art`, and purchase/support handling
   is off-app but first-party. Reword to "the application
   core runs locally" plus explicit server touchpoints.
2. "We do not collect" list (identity, usage, chats, files,
   voice, location, identifiers, history): TRUE for the
   application (no collection SDK found) but INCOMPLETE:
   optional features transmit chats (F6/F7), queries
   (F3/F4), coordinates (F5), and file/download metadata
   (F1/F2/F9) to THIRD parties, and apt/support touch
   FIRST-party servers. The list must gain recipients.
3. Local-processing sections 3.1-3.5: broadly SUPPORTED for
   default flows, with two fixes: STT/TTS audio handling
   should state the transient loopback transport, and the
   biometric "never transmitted externally" line must gain
   the external-provider exception (a voice transcript
   pasted or spoken into an OpenRouter-backed chat leaves
   the machine like any prompt).
4. Model downloads (4.1): SUPPORTED on endpoints; add the HF
   token behavior, the CivitAI API key, and the missing
   gates (F1/F2).
5. Search (4.2): SUPPORTED on DDG; ADD the scrape/crawl
   target-site disclosure, the Scrapy transport caveat, and
   arXiv-as-dormant (or remove the code before release).
6. External providers (4.3): SUPPORTED on OpenRouter/OpenAI;
   ADD the loopback-default vs configurable-remote Ollama
   distinction and the `use_*` defaults.
7. Weather (4.4): SUPPORTED; ADD the triple-gate detail, the
   local ZCTA derivation, and the 1-hour cache.
8. "Operates entirely locally ... only occur when you ..."
   (4.6): INCOMPLETE: omits Kiwix, canvas URL drops,
   vision-URL fetch, apt, and the (future) update check.
9. Storage path (5.1): SUPPORTED (`~/.local/share/airunner`
   default) but must ADD custom-path data outside `<base>`,
   backups, settings files, and plaintext keys.
10. "Uninstalling the Software" deletes data (5.3):
    CONTRADICTED. Uninstall preserves everything; even
    `--delete-data` leaves most files (section 5). Must be
    rewritten with the actual deletion procedure.
11. CPA rights (6.1): "nothing to opt out of" is CONTRADICTED
    for optional online features (there IS something to opt
    out of: six consent flags plus offline mode, subject to
    the section 3 gaps). Consent-by-use for sensitive data
    (6.2) and CPA applicability to a no-collection desktop
    app are COUNSEL questions.
12. Children (section 7), international transfers (section 8),
    open-source pointer (section 10), contact email
    (section 11): CARRY OVER with owner confirmation of the
    contact address and any territory-specific additions
    from counsel.

## 8. Business facts needing owner input (no code source)

- Q1. `apt.airunner.art`: operator, access/error-log
  retention, and whether IPs are stored or shared.
- Q2. Purchase flow: storefront, payment processor(s), what
  buyer data Capsize sees, retention, and refund mechanics.
- Q3. Support flow: support desk/tooling, what user data is
  received and retained, and whether diagnostics exports
  sent to support get special handling.
- Q4. Is a remote (non-loopback) Ollama endpoint exposed in
  any shipped UI or documented configuration? If yes, the
  policy must name it as an online feature.
- Q5. Update manifest host and ship date for the P10 update
  transport (currently unwired): owner confirms the host
  before any policy names it.
- Q6. Confirm the support/contact address (current text uses
  `contact@capsizegames.com`) and the privacy-request
  channel for purchase/support records.
- Q7. Decide the GUI-vs-services consent-store fix (section 3)
  before promising toggle effectiveness; alternatively
  scope the policy to offline mode plus per-feature setup.
- Q8. Confirm the `--delete-data` allowlist vs `settings.ini`
  discrepancy and whether backup/log purge will be added.

## 9. Reviewer and operator fields

- Operator name: PENDING
- Operator date (UTC): 2026-10-09 (static inspection only)
- Reviewer name: PENDING
- Reviewer date (UTC): PENDING
- Candidate: PENDING (base commit `0d551c7c8` inspected, not a
  release candidate)
- Reviewer acceptance: PENDING (issue #2121 stays open until
  this exists)

## 10. Source references

In-checkout: `release-planning/linux-v1/egress-coverage-ledger.md`,
`release-planning/linux-v1/licenses.md`,
`src/airunner/crash_handler.py`, `src/airunner/main.py`,
`src/airunner/daemon_client/`,
`src/airunner/components/application/gui/dialogs/privacy_consent_dialog.py`,
`src/airunner/components/application/gui/windows/main/worker_manager.py`,
`src/airunner/components/application/gui/windows/main/download_model_dialog.py`,
`src/airunner/components/application/gui/dialogs/download_models_dialog.py`,
`src/airunner/components/settings/gui/widgets/privacy_settings/privacy_settings_widget.py`,
`src/airunner/components/settings/gui/windows/settings/airunner_settings.py`,
`src/airunner/components/update/gui/windows/update/update_window.py`,
`src/airunner/components/documents/kiwix_api.py`,
`src/airunner/components/documents/gui/widgets/kiwix_widget.py`,
`src/airunner/components/llm/gui/widgets/bot_preferences.py`,
`src/airunner/components/application/gui/widgets/paths/path_widget.py`,
`src/airunner/components/art/gui/widgets/civitai_preferences/civitai_preferences_widget.py`,
`services/src/airunner_services/url_safety.py`,
`services/src/airunner_services/downloads/policy.py`,
`services/src/airunner_services/downloads/civitai.py`,
`services/src/airunner_services/downloads/huggingface_download_worker.py`,
`services/src/airunner_services/downloads/update_check.py`,
`services/src/airunner_services/llm/utils/model_downloader.py`,
`services/src/airunner_services/tools/web_tools.py`,
`services/src/airunner_services/tools/web_content_extractor.py`,
`services/src/airunner_services/tools/search_providers/`,
`services/src/airunner_services/llm/tools/intelligent_crawl_tool.py`,
`services/src/airunner_services/llm/managers/agent/weather_mixin.py`,
`services/src/airunner_services/utils/location/get_lat_lon.py`,
`services/src/airunner_services/llm/adapters/chat_model_factory_model_builders.py`,
`services/src/airunner_services/llm/adapters/chat_model_factory_provider_creation.py`,
`services/src/airunner_services/llm/adapters/mixins/generation_vision_inputs.py`,
`services/src/airunner_services/api/server.py`,
`services/src/airunner_services/api/loopback_token.py`,
`services/src/airunner_services/runtimes/daemon_config.py`,
`services/src/airunner_services/database/upgrade_backup.py`,
`services/src/airunner_services/database/models/`,
`services/src/airunner_services/kiwix_api.py`,
`debian/vendor/airunner_common/settings.py`,
`debian/vendor/airunner_common/logging_utils.py`,
`debian/airunner.prerm`, `packaging/linux/UNINSTALL.md`,
`packaging/linux/uninstall.sh`, `README.md`, `SECURITY.md`,
`LICENSE`, `NOTICE`, `RELICENSING.md`.
Upstream policies linked from the drafts (HF, CivitAI,
Open-Meteo, OpenRouter, OpenAI, DuckDuckGo, Kiwix, arXiv)
were NOT re-verified in this session; counsel should confirm
the links and quote nothing from them.
