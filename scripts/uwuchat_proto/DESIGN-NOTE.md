# #2230 phase 1 — design note (decisions 1–4 + endpoint inventory)

Author: implementation session, 2026-09-18. Scope: design + inventory only.
No prototype code is described here; phase 2 is separate.

## Method / evidence

Read-only. No server was started, no database opened, no network call made to
the web deployment. Sources inspected:

- UwUChat client: `airunnerweb` `projects/uwuchat/client/` (on `master`).
- Framework client: `airunnerweb` `client/src/` (`api/`, `features/`).
- Desktop daemon: `Capsize-Games/airunner`
  `services/src/airunner_services/api/` (`server.py`, `routes/`).
- Companion backend already ported for #2083/#216:
  `services/src/airunner_services/llm/companion/`.

## The finding that sets the shape: the client has no REST layer

`client/src/api/client-base.ts` no longer issues HTTP. `request()` delegates to
`rpcRequest()` over **one** persistent WebSocket at `/api/v1/events`
(`client/src/features/api/WsApiClient.ts`). Every `/api/v1/...` string in the
client is a **logical RPC path** dispatched server-side by that socket, and the
server **pushes a bootstrap payload on connect** (including `chatbots`). The
client also opens two more sockets:

| Purpose | URL | Evidence |
|---|---|---|
| All request/response + events + bootstrap | `ws://<host>/api/v1/events` | `WsApiClient.ts:27`, `:104` |
| Chat token stream | `ws://<host>/api/v1/llm/stream` | `client/src/features/llm/useLLMWebSocket.ts:14` |
| TTS audio | `ws://<host>/api/v1/tts/ws` | `projects/uwuchat/client/api/chat.ts:136` |

The desktop daemon currently has **none** of: an `/api/v1/events` socket, the
RPC envelope (`{type:"rpc_request", id, method, path, body}` →
`{type:"rpc_response", id, status, body, binary}`), or a bootstrap push. This
is the single biggest delta in #2230 and it is an architectural one, not a set
of missing handlers.

---

## Decision 1 — where the desktop chat UI source lives

**Answer: a desktop build target inside `airunnerweb` that emits a versioned,
self-contained static bundle; the desktop pins the version. No sibling
checkout.**

- Precedent already exists and is documented: the `AIRUNNER_PROJECT` root-swap
  and per-product builds (CLAUDE.md "Independent per-product builds",
  issue #258 — `projects/uwuchat/client` and `projects/airunner-art/client`
  each have their own `package.json` / `vite.config.ts` / `main.tsx` and build
  independently).
- Add a third target whose `App.tsx` roots only the in-scope surface. Because
  the in-scope surface is a whole app shell, a build-time root swap is the
  correct shape here — the same reasoning CLAUDE.md gives for the existing
  `virtual:app-root` swap, not a shared component with a slot prop.
- **Cloud-only code is excluded at build time** by that target never importing
  the auth / subscription / social / rooms / economy / admin modules. This is
  the only way to satisfy both #2230 ("excluded from the desktop build, not
  hidden in the UI") and #2230's acceptance test ("inspecting the built
  bundle"). A runtime feature-flag is explicitly rejected.
- The desktop consumes the output as a **versioned artifact** (npm package or
  release tarball published by CI, e.g.
  `@airunner/uwuchat-desktop-chat@<semver>`), unpacked into the desktop's
  package data dir. It is not a `file:` reference into a sibling working copy,
  so the coupling that #2185 removed does not return.
- The "shared package" option is rejected as the primary shape: the unit under
  reuse is an app shell (routing, providers, layout), not a component library.

## Decision 2 — API boundary

**Answer: implement the needed subset of UwUChat's contract on the desktop
daemon, and put the *transport* (events RPC envelope + bootstrap) into the
shared contract in `airunnerweb#260` — do not hand-write an ad hoc adapter.**

Two halves, with very different costs:

- **Resource half — already coincides.** The client's resource calls
  (`client/src/api/settings.ts`) are:
  `POST /api/v1/settings/resources/{R}/query`, `GET|PUT
  /api/v1/settings/resources/{R}/singleton`,
  `PUT|DELETE /api/v1/settings/resources/{R}/{id}`. The desktop exposes
  exactly these paths (`routes/domain_resource_router.py`, mounted at
  `/api/v1/settings`) and even maps resource name `"Chatbot"` to the
  `chatbots` table (`daemon_client/resource_store.py:22,101`). So the resource
  vocabulary is shared; what is missing is (a) a `"Chatbot"` entry in
  `domain_resource_registry.py` (today the settings singletons are a fixed
  art/LLM set) and (b) the RPC envelope.
- **`/api/v1/llm/*` half — paths exist, contracts do not.** The desktop has
  `/api/v1/llm/stream` and `/api/v1/llm/conversations*`, but the stream
  envelope differs: the desktop emits `{type, content, done}` and parses via
  `parse_stream_message` (`routes/llm_stream_routes.py`), while the client
  consumes `{token, message_type, done, call_chain_id, tool_status, ...}`. The
  desktop's conversation routes are closer, but still need field-level
  alignment (mood, sessions, call chains).

Recommendation: implement the client's `/api/v1/llm/*` contract shape rather
than translate, and **add the events-RPC envelope + bootstrap schema to
`airunner-contracts`**. #260 as written covers runtime invocation contracts
(19 message classes, request/response, descriptors); it does **not** cover the
events bus or bootstrap, so relying on it as-is would silently produce the ad
hoc translation layer this issue warns against. The desktop already has a
frozen backend contract to align against:
`llm/companion/contracts.py` (`ChatbotId`, `SessionId`,
`CompanionTurnRequest`, error codes) from #216.

## Decision 3 — how the page loads inside Qt

**Answer: daemon-served static assets over loopback, authenticated with the
existing loopback token, with loopback-only egress enforced by a QtWebEngine
interceptor + CSP.**

- Serve the built bundle from the daemon at `http://127.0.0.1:<port>/`. This
  keeps `wsHost()`/`location.host` working unchanged and lets the page use the
  same `/api/v1/*` paths. (`qrc:`/`file:` would force host rewrites.)
- Auth: reuse `loopback_token.py` (file at
  `AIRUNNER_BASE_PATH/config/loopback_token`, mode 0600; accepted as
  `x-airunner-token` or `Authorization: Bearer` —
  `api/server.py:130`). WebSockets cannot set headers, so the token must also
  be accepted in the query string (`?token=`), mirroring the web convention.
  `authenticate_connection` currently reads the bearer header; the events and
  stream sockets need the query-token path added.
- **No remote requests**: install a `QWebEngineUrlRequestInterceptor` that
  blocks every non-loopback URL, and set a restrictive CSP. This is the
  enforcement point for #2083's global egress policy and makes #2230's
  "verified by a test, not by inspection" acceptance achievable.
- The QWebChannel bridge option is rejected as primary (extra surface for no
  gain; the client is already a network client). It remains a fallback if
  browser mic capture for STT is ever needed.
- Note the current chat widget *enables* remote access
  (`conversation_webengine_page.py` sets
  `LocalContentCanAccessRemoteUrls = True`); the new page must not inherit
  that.

## Decision 4 — existing desktop conversation data

**Answer: read in place. No migration.**

- #2083 requires preserving data; #2230 acceptance requires old conversations
  to remain visible. A rewrite risks data loss for no benefit.
- The daemon maps its own rows into the contract shapes at request time:
  desktop `Conversation` (`chatbot_id`, `chatbot_name`, `user_data`) covers the
  client's "conversation"; the already-ported companion tables
  (`CompanionSession`, `CompanionTurn`) cover the client's
  `chatbot-session` / `thread`. Where the client needs a field that does not
  exist, add a read-only projection in the daemon — never a schema migration.
- `#2230`'s "no data loss either way" is satisfied by construction, and this
  keeps the change reversible at the gate.

## Decision 5 — sequencing vs Linux v1

Owner's call. Not addressed here.

---

## In-scope endpoint inventory (client → desktop daemon)

Transport note: `RPC` = client sends this over the `/api/v1/events` WebSocket.
`PATH MATCH` means the desktop exposes the same path; it still needs the RPC
envelope unless stated otherwise.

### Streaming (in scope)

| Client call | Desktop equivalent | Status |
|---|---|---|
| `WS /api/v1/llm/stream` | `routes/llm_stream_routes.py` `@router.websocket("/stream")` | **Path exists; envelope mismatch** |
| cancel frame | `cancel` handling in the same socket | Verify frame names align |

### Conversation list / new / select / delete (in scope)

| Client call | Desktop equivalent | Status |
|---|---|---|
| `GET /api/v1/llm/conversations` | `conversations.py:58` | **PATH MATCH** |
| `POST /api/v1/llm/conversations` | `conversations.py:66` | **PATH MATCH** |
| `DELETE /api/v1/llm/conversations/{id}` | `conversations.py:138` | **PATH MATCH** |
| `GET /api/v1/llm/conversations/session` | `conversations.py:86` | **PATH MATCH** |
| `POST /api/v1/llm/conversations/select` | `conversations.py:104` | **PATH MATCH** |
| `POST /api/v1/llm/conversations/truncate` | — | **GAP** |
| `POST /api/v1/llm/conversations/previews` | closest: `GET /conversations/{id}/summary` | **GAP** (shape differs) |
| `DELETE /api/v1/llm/chatbot/{id}/messages/{idx}` | — | **GAP** |

### UwU thread / session (in scope)

| Client call | Desktop equivalent | Status |
|---|---|---|
| `GET /api/v1/llm/chatbot-session?chatbot_id=` | — | **GAP** (→ companion session) |
| `GET /api/v1/llm/thread?chatbot_id=&limit=&offset=` | — | **GAP** (→ conversation messages / turns) |

### Chatbot / persona selection (in scope)

| Client call | Desktop equivalent | Status |
|---|---|---|
| bootstrap `payload.chatbots` (push on `/api/v1/events`) | — | **GAP** (no events socket/bootstrap) |
| `POST /api/v1/settings/resources/Chatbot/query` | `domain_resource_router.py` query route | **PATH MATCH**; `Chatbot` not in `domain_resource_registry.py` → **GAP** |
| `PUT /api/v1/settings/resources/Chatbot/{id}` | `domain_resource_router.py` update route | **PATH MATCH**; same registry **GAP** |
| default/current chatbot selection | `llm/get_chatbot.py` (`current` flag) | present, needs contract mapping |

### Models / health / hardware (in scope, supporting)

| Client call | Desktop equivalent | Status |
|---|---|---|
| `GET /api/v1/art/bootstrap` | `catalog_bootstrap.py:52` | **PATH MATCH**; payload shape to verify |
| `GET /api/v1/health` | `health.py:61` | **PATH MATCH** |
| `GET /api/v1/daemon/hardware` | `hardware.py:45` | **PATH MATCH** |

### Voice hooks (in scope = "hooks for desktop STT/TTS")

| Client call | Desktop equivalent | Status |
|---|---|---|
| `WS /api/v1/tts/ws` | served (`tts_ws.py`): `{"type":"synthesize","text","voice","speed"}` → `{"type":"audio","data":"<base64 WAV>"}` | **DONE** |
| STT | served (`stt.py`): `WS /api/v1/stt/stream` takes a `{"type":"transcribe","audio":"<base64>","language"}` frame (or a raw binary audio frame) → `{"type":"transcript","text","language","final"}`; the client toggle still needs to send a frame | **DONE (desktop)**; client stub remains |

### Excluded at build time (out of scope per #2230)

auth (`/api/v1/auth/*`, OAuth, invite, verification), subscription/quota
(`/api/v1/usage/quota`, Stripe admin), social connectors
(`/api/v1/bluesky|itch|spotify|steam/*`), rooms (`/api/v1/rooms/*`,
`/uwu-dms/*`), economy/gems (`/items`, `/cards`), admin
(`/api/v1/admin/*`), push (`/api/v1/push/*`), weather/geocode, `fastsearch`,
and the UwU Creator surface (`generate-character`, `generate-uwu-identity`,
`uwu-greeting`, `create-random-chatbot`). None of these may be imported by the
desktop target (decision 1).

## Gap summary (counted)

- 1 architectural gap: `/api/v1/events` RPC envelope + bootstrap.
- 1 envelope mismatch: `/api/v1/llm/stream`.
- 5 missing REST/RPC routes: `conversations/truncate`,
  `conversations/previews`, `chatbot/{id}/messages/{idx}`, `chatbot-session`,
  `thread`.
- 1 registry gap: `Chatbot` not registered as a resource domain.
- 1 voice gap: `/api/v1/tts/ws` (and client-side STT stub).
- Bundle-size / build-time exclusion verification is part of phase 3.

## Risks / items to freeze before phase 3

1. The exact `/api/v1/events` frame schema (rpc_request/rpc_response,
   subscribe, bootstrap) — must land in `airunner-contracts`, not be invented
   twice.
2. The `/api/v1/llm/stream` chunk schema (`token`, `message_type`,
   `call_chain_id`, `tool_status`) shared with the web engine.
3. Query-string token acceptance on the events + stream sockets.
4. A build-inspection test proving no cloud-only module is in the bundle.
5. A loopback-only egress test (interceptor + CSP).
