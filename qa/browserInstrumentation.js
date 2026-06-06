// qa/browserInstrumentation.js
// Injected by the QA runner only. Never import this from app code.

window.__errors = [];
window.__wsEvents = [];
window.__qaReady = false;

window.addEventListener('error', (e) => {
  window.__errors.push({
    type: 'uncaught',
    message: e.message,
    source: e.filename,
    line: e.lineno,
    col: e.colno,
    stack: e.error?.stack ?? null,
    ts: Date.now()
  });
});

window.addEventListener('unhandledrejection', (e) => {
  window.__errors.push({
    type: 'unhandledrejection',
    message: String(e.reason),
    stack: e.reason?.stack ?? null,
    ts: Date.now()
  });
});

const OriginalWebSocket = window.WebSocket;
window.WebSocket = function(url, protocols) {
  const ws = protocols
    ? new OriginalWebSocket(url, protocols)
    : new OriginalWebSocket(url);

  ws.addEventListener('open', () =>
    window.__wsEvents.push({ dir: 'open', url, ts: Date.now() }));
  ws.addEventListener('close', (e) =>
    window.__wsEvents.push({ dir: 'close', url, code: e.code, reason: e.reason, ts: Date.now() }));
  ws.addEventListener('error', () => {
    window.__wsEvents.push({ dir: 'error', url, ts: Date.now() });
    window.__errors.push({ type: 'websocket_error', url, ts: Date.now() });
  });
  ws.addEventListener('message', (e) => {
    let parsed = e.data;
    try { parsed = JSON.parse(e.data); } catch (_) {}
    window.__wsEvents.push({ dir: 'in', url, data: parsed, ts: Date.now() });
  });

  const origSend = ws.send.bind(ws);
  ws.send = function(data) {
    let parsed = data;
    try { parsed = JSON.parse(data); } catch (_) {}
    window.__wsEvents.push({ dir: 'out', url, data: parsed, ts: Date.now() });
    return origSend(data);
  };

  return ws;
};
window.WebSocket.prototype = OriginalWebSocket.prototype;

window.__qaReady = true;
