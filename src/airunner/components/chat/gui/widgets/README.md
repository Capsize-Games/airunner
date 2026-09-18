# Chat GUI Widgets

Widgets for the chat UI: the Qt prompt/composer widget and the
first-class host for the desktop chat surface.

## Components

- `chat_surface_widget.py`: hosts the built chat client in a
  `QWebEngineView`, loaded from the daemon over loopback. The surface
  owns its own sidebar, transcript and composer.
- `chat_surface_interceptor.py`: refuses every non-loopback request and
  attaches the loopback token to the rest (including WebSocket
  handshakes, which the page cannot authenticate itself).
- `chat_prompt_widget.py`: the Qt prompt/composer widget used by the chat
  and generator tabs. It drives the daemon and asks the hosted surface to
  re-read the conversation when a turn starts or finishes.
- `templates/`: Qt Designer `.ui` sources and their generated `_ui.py`
  modules.

## Text field rendering

- Edit `.ui` files for layout/structure changes, then run
  `python scripts/build_ui.py` from a checkout.
- Do **not** edit `*_ui.py` files directly.
- Transcript rendering and chat styling live in the hosted client
  (`projects/airunner-desktop/client` in the web repo), not in this
  package.

## The hosted chat surface (issue #2230)

- The daemon serves the bundle
  (`airunner_services.api.routes.client_bundle`) so the page's origin is
  the same as `/api/v1/*` and the client's `wsHost()` keeps resolving to
  the daemon — no build-time host override.
- The daemon mounts it only when `AIRUNNER_CLIENT_BUNDLE` points at a
  built bundle that contains `index.html`; otherwise routing is
  unchanged.
- `airunner/components/chat/gui/chat_surface_endpoint.py` is the single
  place that resolves the daemon origin and the loopback token.
- `scripts/chat_surface_smoke.py` renders the surface through this host
  against the real daemon and reports the page text plus the events
  socket result. It needs a display.
- Remote access stays off (`LocalContentCanAccessRemoteUrls` is
  explicitly disabled) and every request passes the interceptor.

## Safety & best practices

- Persistence stays server-side; the hosted page is a client of the
  daemon.
- All code follows DRY, KISS, and type-hinting guidelines.

---

For more details, see the main project README and architecture
documentation.
