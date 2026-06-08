# Live Stroke Sync — Implementation Plan

Real-time collaborative drawing: remote sessions see each other's strokes as they happen, not just on commit.

---

## Problem statement

Currently the canvas only syncs on `pointerup` (when `onAddStroke` is called and a full `getPersistableState()` snapshot is sent). A remote tab sees nothing until the stroke is finished.

---

## Approach: delta messages + ghost strokes

Send only the **new points** accumulated since the last flush (the delta), at a throttled interval (~80 ms). The receiving tab renders a **ghost stroke** — a transient Konva Line that lives outside React state and outside undo history. When the stroke is committed (mouseup), the ghost is replaced by the normal committed stroke arriving in the next full-document sync.

---

## Message protocol

Two new WS message types, relay-only — the server never persists them.

### `stroke:live` (sender → server → other tabs)

```json
{
  "type": "stroke:live",
  "sessionId": "uuid-v4",
  "layerId": "layer-abc",
  "strokeId": "stroke-xyz",
  "tool": "brush",
  "color": "#ff0000",
  "strokeWidth": 12,
  "delta": [x1, y1, x2, y2, ...]
}
```

- `delta` contains only the points appended since the previous flush — not the full growing array.
- `strokeId` is a stable identifier for this stroke, generated at `pointerdown`. Lets the receiver distinguish strokes across layers/sessions.

### `stroke:end` (sender → server → other tabs)

```json
{
  "type": "stroke:end",
  "sessionId": "uuid-v4",
  "strokeId": "stroke-xyz"
}
```

Sent on `pointerup`. Tells other tabs to discard the ghost for this session. The full-document sync that immediately follows will carry the committed stroke.

---

## Changes required

### 1. Server — `canvas_document.py`

Extend the WS message loop to recognise the two new types and relay them without touching the DB.

```python
# inside the `while True:` loop, before the existing `doc = data.get("document")` block:

msg_type = data.get("type")

if msg_type in ("stroke:live", "stroke:end"):
    # Relay to all other clients, no persistence.
    await _broadcast_raw(data, sender=websocket)
    continue

# existing document-persistence path below...
```

Add `_broadcast_raw` (analogous to `_broadcast_document` but takes the raw dict):

```python
async def _broadcast_raw(payload: dict, sender: WebSocket) -> None:
    stale: list[WebSocket] = []
    for client in _connected_clients:
        if client is sender:
            continue
        try:
            await client.send_json(payload)
        except Exception:
            stale.append(client)
    for s in stale:
        _connected_clients.discard(s)
```

### 2. `useCanvasSync.ts` — new callbacks + send helpers

Add two new optional callbacks to `UseCanvasSyncOptions`:

```ts
onLiveStroke?: (msg: LiveStrokeMessage) => void;
onStrokeEnd?:  (msg: StrokeEndMessage)  => void;
```

And two new send helpers on `UseCanvasSyncReturn`:

```ts
sendLiveStroke: (msg: LiveStrokeMessage) => void;
sendStrokeEnd:  (msg: StrokeEndMessage)  => void;
```

Update `ws.onmessage` to dispatch on `data.type`:

```ts
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "document")     onDocumentRef.current(data.document ?? null);
  if (data.type === "stroke:live")  onLiveStrokeRef.current?.(data);
  if (data.type === "stroke:end")   onStrokeEndRef.current?.(data);
};
```

Types to add (e.g. `canvasSyncTypes.ts`):

```ts
export interface LiveStrokeMessage {
  type: "stroke:live";
  sessionId: string;
  layerId: string;
  strokeId: string;
  tool: "brush" | "eraser";
  color: string;
  strokeWidth: number;
  delta: number[];
}

export interface StrokeEndMessage {
  type: "stroke:end";
  sessionId: string;
  strokeId: string;
}
```

### 3. `CanvasStage.tsx` — throttled delta sending

**Session identity** — generate once on mount, stable for the tab's lifetime:

```ts
const sessionId = useRef(crypto.randomUUID());
```

**Per-stroke tracking** — reset at `pointerdown`:

```ts
const liveStrokeId   = useRef<string>("");
const lastSentCount  = useRef(0);        // how many points were in the last flush
const liveThrottleRef = useRef<ReturnType<typeof setTimeout> | null>(null);
```

**`handleOverlayPointerDown`** — assign a fresh `strokeId`, reset counter:

```ts
liveStrokeId.current  = crypto.randomUUID();
lastSentCount.current = 0;
```

**`handleOverlayPointerMove`** — schedule a throttled flush (don't send on every move event):

```ts
if (!liveThrottleRef.current) {
  liveThrottleRef.current = setTimeout(() => {
    liveThrottleRef.current = null;
    const pts = drawingPoints.current;
    const delta = pts.slice(lastSentCount.current);
    if (delta.length === 0) return;
    lastSentCount.current = pts.length;
    canvasSync.sendLiveStroke({
      type: "stroke:live",
      sessionId: sessionId.current,
      layerId: activeLayerId!,
      strokeId: liveStrokeId.current,
      tool: activeTool as "brush" | "eraser",
      color: brushColor,
      strokeWidth: brushSize,
      delta,
    });
  }, 80);
}
```

**`handleOverlayPointerUp`** — cancel any pending flush, send `stroke:end`:

```ts
if (liveThrottleRef.current) {
  clearTimeout(liveThrottleRef.current);
  liveThrottleRef.current = null;
}
canvasSync.sendStrokeEnd({
  type: "stroke:end",
  sessionId: sessionId.current,
  strokeId: liveStrokeId.current,
});
lastSentCount.current = 0;
```

### 4. Ghost stroke state + rendering

Ghost strokes must **not** enter `useCanvasState` — no React state, no history, no persistence.

Store them in a module-level ref map managed by a new hook `useGhostStrokes.ts`:

```ts
// Map<sessionId, { layerId, strokeId, tool, color, strokeWidth, points[] }>
type GhostStroke = {
  layerId: string; strokeId: string;
  tool: "brush" | "eraser"; color: string; strokeWidth: number;
  points: number[];
};
```

The hook exposes:
- `applyLiveDelta(msg: LiveStrokeMessage)` — appends delta to the ghost for `msg.sessionId`
- `clearGhost(sessionId: string)` — called on `stroke:end` or new `document`
- `getGhostLines(layerId: string)` — returns all ghost Konva Line configs for a given layer

**Rendering** — add a single non-listening Konva `Layer` at the top of the stage (above content, below the brush indicator) that renders all active ghost Lines imperatively. Update it via `batchDraw()` inside `applyLiveDelta` — no React re-renders involved.

```tsx
<Layer ref={ghostLayerRef} listening={false}>
  {/* populated imperatively by useGhostStrokes */}
</Layer>
```

### 5. `CanvasPanel.tsx` — wire everything up

Pass the new callbacks into `useCanvasSync`:

```ts
const canvasSync = useCanvasSync({
  onDocument:   (json) => { if (json) canvas.loadFromJSON(json); },
  onLiveStroke: ghostStrokes.applyLiveDelta,
  onStrokeEnd:  (msg)  => ghostStrokes.clearGhost(msg.sessionId),
});
```

Pass `sendLiveStroke` / `sendStrokeEnd` down to `CanvasStage` via props (or surface them through a context ref — whichever avoids prop-drilling most cleanly given the current structure).

---

## Ghost stroke lifecycle

```
pointerdown  → strokeId assigned, lastSentCount = 0
pointermove  → throttle fires every 80 ms → sendLiveStroke(delta)
             → remote tab: applyLiveDelta → append points → batchDraw
pointerup    → sendStrokeEnd → remote tab: clearGhost(sessionId)
             → full document sync arrives → committed stroke rendered normally
```

---

## What does NOT change

| Concern | Status |
|---|---|
| `useCanvasState` / undo history | Untouched — ghosts never enter state |
| Persistence / IndexedDB | Untouched — `stroke:live` is never stored |
| `loadFromJSON` timestamp guard | Untouched — only full-document messages go through it |
| Existing commit-on-mouseup sync | Untouched — still happens, still the source of truth |

---

## Scope summary

| File | Change |
|---|---|
| `canvas_document.py` | Add `_broadcast_raw`; relay `stroke:live` / `stroke:end` without DB write |
| `canvasSyncTypes.ts` | New file — `LiveStrokeMessage`, `StrokeEndMessage` types |
| `useCanvasSync.ts` | New callbacks + send helpers; extend `onmessage` dispatch |
| `CanvasStage.tsx` | `sessionId` ref; throttled delta send in move; `stroke:end` on up |
| `useGhostStrokes.ts` | New hook — ghost map, `applyLiveDelta`, `clearGhost`, imperative Konva updates |
| `CanvasPanel.tsx` | Wire `onLiveStroke` / `onStrokeEnd` into sync; pass send helpers to stage |

---

## Open questions before starting

1. **Cursor indicator** — should remote cursors show a brush-ring at the ghost stroke's latest point? Adds polish but is a separate concern.
2. **Throttle interval** — 80 ms is a reasonable starting point (~12 fps of stroke updates). Worth making it configurable or auto-scaling based on WS latency?
3. **Multi-layer ghosts** — if a remote user switches layers mid-stroke the ghost should follow. The current plan handles this since `layerId` is per-message, but the ghost layer needs to render in the correct layer position in the stack if we want correct z-ordering. Simplest first cut: render all ghosts in a single top-level overlay layer (above all content). Revisit if z-order matters.
