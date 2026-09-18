# #2230 phase-2 prototype — transport plumbing

Branch `2230-uwuchat-qt-prototype`. Throwaway. Not wired into the app.

## What this demonstrates

The integration architecture from the [#2230 design
note](https://github.com/Capsize-Games/airunner/issues/2230#issuecomment-5735328537):

- a page loaded in **QtWebEngine** from **loopback** HTTP;
- the UwUChat client's real transport contract —
  `ws /api/v1/events` (`rpc` -> `rpc_response`, `bootstrap`) and
  `ws /api/v1/llm/stream` (`chat` -> `chunk`/`thinking`/`mood`);
- **loopback-only egress** enforced by a `QWebEngineUrlRequestInterceptor`;
- the existing loopback token as the credential.

## What this does NOT demonstrate (honest scope)

- **Not the real UwUChat UI.** It is a 60-line stand-in page. The real
  React surface needs the new desktop build target that does not exist
  yet in `airunnerweb` (decision 1), and building the current `uwuchat`
  target would ship cloud-only code, which #2230 forbids.
- **No real model.** No model is downloaded (and loading one is out of
  scope here), so replies are canned. "Streaming end to end" is proven
  for the transport, not for inference.
- **No database.** Nothing reads or writes the desktop SQLite data, so
  the run is safe regardless of `AIRUNNER_BASE_PATH`.

## Run

```sh
cd airunnerdesktop/scripts
AIRUNNER_BASE_PATH=../tmp/airunner-base \
PROTO_SHOT=../tmp/uwuchat_proto.png \
../venv/bin/python -m uwuchat_proto.qt_host
```

Needs a display (`DISPLAY`). The window loads, auto-sends one message,
streams the canned reply over the loopback socket, then writes the
screenshot and exits.
