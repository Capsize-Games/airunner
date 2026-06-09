# Canvas Tool Pattern

This document defines the **one true pattern** for adding a new canvas tool (or
tool setting) to the AI Runner canvas.  Read this before touching any canvas
tool code.

---

## Directory layout

```
src/features/canvas/
├── stage/
│   ├── StageContent.tsx          ← Konva <Stage> + tool layer wiring (JSX only)
│   ├── tools/
│   │   ├── lasso/
│   │   │   ├── useLassoTool.ts   ← interaction hook
│   │   │   └── LassoLayer.tsx    ← Konva rendering component
│   │   └── select/
│   │       ├── useSelectTool.ts
│   │       └── SelectLayer.tsx
│   └── …                         ← zoom, keyboard, drawingOverlay, moveTool, …
├── sidebar/
│   ├── LassoControls.tsx         ← tool settings UI (shown in left panel)
│   ├── BrushControls.tsx
│   └── MoveControls.tsx
├── state/
│   ├── lasso.ts                  ← persisted tool settings setters
│   ├── brush.ts
│   └── …
├── canvasTypes.ts                ← CanvasState fields (add per-tool settings here)
├── canvasStateUtils.ts           ← defaultState() (add defaults here)
├── useCanvasState.ts             ← compose all state hooks
└── CanvasStage.tsx               ← thin orchestrator (calls hooks, passes to StageContent)
```

---

## The two-file rule per tool

Every tool that has **canvas interaction** (mouse events, keyboard shortcuts,
visual overlay) requires exactly **two files** inside `stage/tools/<toolName>/`:

| File | Purpose |
|------|---------|
| `use<Tool>Tool.ts` | All state, refs, and event handlers. No JSX. |
| `<Tool>Layer.tsx` | Pure Konva rendering. No interaction logic. |

Tools that only have **settings** (no canvas overlay) need only the
`sidebar/` and `state/` pieces below.

---

## Step-by-step: add a new tool

### 1 — Create the interaction hook

**`stage/tools/<tool>/use<Tool>Tool.ts`**

```ts
import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";

// What the rendering layer needs
export interface <Tool>RenderState {
  // … add fields required for rendering
}

export interface Use<Tool>ToolReturn {
  renderState: <Tool>RenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp:   (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

export function use<Tool>Tool({
  isActive,
  getCanvasPos,
  // … add stageRef if you need cursor changes or stage queries
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
}): Use<Tool>ToolReturn {

  // State that drives re-renders
  const [foo, setFoo] = useState(…);

  // Refs for synchronous cross-handler access (no re-render cost)
  const fooRef = useRef(…);

  // Reset when the tool is deactivated
  useEffect(() => {
    if (!isActive) { /* reset all state + refs */ }
  }, [isActive]);

  // Own global pointerup listener — catches releases outside the Stage
  useEffect(() => {
    const onGlobalUp = () => { /* … */ };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup",   onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup",   onGlobalUp);
    };
  }, [/* stable deps only */]);

  // Return true from handlers when the event is consumed
  const onMouseDown = useCallback((e): boolean => {
    if (!isActive || e.evt.button !== 0) return false;
    // … handle event
    return true;
  }, [isActive, getCanvasPos]);

  const onMouseMove = useCallback((e): boolean => {
    if (!isActive) return false;
    // … update rendering state
    return true;
  }, [isActive, getCanvasPos]);

  const onMouseUp = useCallback((e): boolean => {
    if (!isActive) return false;
    // … commit result
    return true;
  }, [isActive, getCanvasPos]);

  return {
    renderState: { foo },
    onMouseDown, onMouseMove, onMouseUp,
  };
}
```

**Return-value contract**

* `onMouseDown / onMouseMove / onMouseUp` return **`true`** when they consumed
  the event, **`false`** when they didn't (tool inactive or event irrelevant).
* The chain in `CanvasStage.tsx` uses `if (tool.onMouseDown(e)) return;` so the
  first matching tool wins.
* Each hook owns its own global `pointerup`/`mouseup` listener.  Do **not** add
  tool logic to `CanvasStage`'s global listener.

---

### 2 — Create the rendering component

**`stage/tools/<tool>/<Tool>Layer.tsx`**

```tsx
import { Layer, … } from "react-konva";
import type { <Tool>RenderState } from "./<tool>Tool";  // or the hook file

interface Props extends <Tool>RenderState {}

export default function <Tool>Layer({ /* destructure renderState */ }: Props) {
  // Early-exit if there's nothing to draw
  if (/* nothing visible */) return null;

  return (
    <Layer listening={false}>
      {/* Pure Konva shapes — no event handlers, no hooks */}
    </Layer>
  );
}
```

Rules:
* No `useState`, `useRef`, or event callbacks.
* Wrap everything in `<Layer listening={false}>` unless you intentionally need
  Konva hit-testing on this layer.
* Return `null` rather than an empty `<Layer>` when there is nothing to paint.

---

### 3 — Wire into `CanvasStage.tsx`

```tsx
// 1. Import the hook
import { use<Tool>Tool } from "./stage/tools/<tool>/use<Tool>Tool";

// 2. Call it (alongside the existing tool hooks)
const myTool = use<Tool>Tool({
  isActive: activeTool === "<tool>",
  getCanvasPos,
  // stageRef if needed
});

// 3. Chain the handlers — add one line per handler
const handleMouseDown = useCallback((e) => {
  if (e.evt.button === 1) { /* panning */ return; }
  if (isMoveActive)         { moveToolHandlers.handleMoveMouseDown(e); return; }
  if (lasso.onMouseDown(e)) return;
  if (select.onMouseDown(e)) return;
  if (myTool.onMouseDown(e)) return;   // ← add here
}, [/* include myTool.onMouseDown in deps */]);

// 4. Pass renderState to StageContent
<StageContent
  …
  myToolRenderState={myTool.renderState}   // ← add prop
/>
```

---

### 4 — Wire into `StageContent.tsx`

```tsx
// 1. Import types + component
import <Tool>Layer from "./tools/<tool>/<Tool>Layer";
import type { <Tool>RenderState } from "./tools/<tool>/use<Tool>Tool";

// 2. Add to Props interface
interface Props {
  …
  myToolRenderState: <Tool>RenderState;
}

// 3. Destructure in the function signature
export default function StageContent({ …, myToolRenderState }: Props) { … }

// 4. Render in the "Tool overlays" section at the bottom of <Stage>
{activeTool === "<tool>" && (
  <MyToolLayer {...myToolRenderState} />
)}
```

---

## Step-by-step: add tool settings

Tool settings are **persisted** in `CanvasState` (localStorage + IndexedDB) and
exposed via React Context so any component can read or write them.

### 1 — Add fields to `canvasTypes.ts`

```ts
export interface CanvasState {
  …
  myToolSomeFlag: boolean;
  myToolRadius:   number;
}
```

### 2 — Add defaults to `canvasStateUtils.ts`

```ts
export const defaultState = (): CanvasState => {
  const base = {
    …
    myToolSomeFlag: true,
    myToolRadius:   10,
  };
  …
};
```

### 3 — Create `state/myTool.ts`

```ts
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function myTool({ setState }: CanvasSetters) {
  const setMyToolSomeFlag = useCallback(
    (value: boolean) => setState((prev) => ({ ...prev, myToolSomeFlag: value })),
    [setState],
  );
  const setMyToolRadius = useCallback(
    (value: number) => setState((prev) => ({
      ...prev, myToolRadius: Math.max(0, Math.min(100, value)),
    })),
    [setState],
  );
  return { setMyToolSomeFlag, setMyToolRadius };
}
```

### 4 — Compose into `useCanvasState.ts`

```ts
import { myTool as myToolHook } from "./state/myTool";

export function useCanvasState() {
  …
  const myToolAPI = myToolHook(setters);
  return { …state, …myToolAPI, … };
}
```

### 5 — Create `sidebar/MyToolControls.tsx`

```tsx
import { useCanvasContext } from "../CanvasContext";

export default function MyToolControls() {
  const canvas = useCanvasContext();
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <label>
        <input
          type="checkbox"
          checked={canvas.myToolSomeFlag}
          onChange={(e) => canvas.setMyToolSomeFlag(e.target.checked)}
        />
        Some flag
      </label>
      {canvas.myToolSomeFlag && (
        <input
          type="range" min={0} max={100}
          value={canvas.myToolRadius}
          onChange={(e) => canvas.setMyToolRadius(Number(e.target.value))}
        />
      )}
    </div>
  );
}
```

### 6 — Wire into `CanvasPanel.tsx`

```tsx
import MyToolControls from "../../features/canvas/sidebar/MyToolControls";

const showMyToolControls = !showImagePrompt && canvas.activeTool === "<tool>";

{showMyToolControls && <MyToolControls />}
```

---

## Naming conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Tool id | lowercase, matches `ActiveTool` union | `"lasso"` |
| Hook file | `use<PascalTool>Tool.ts` | `useLassoTool.ts` |
| Layer file | `<PascalTool>Layer.tsx` | `LassoLayer.tsx` |
| State module | `state/<camelTool>.ts` | `state/lasso.ts` |
| Controls component | `<PascalTool>Controls.tsx` | `LassoControls.tsx` |
| RenderState type | `<PascalTool>RenderState` | `LassoRenderState` |
| Hook return type | `Use<PascalTool>ToolReturn` | `UseLassoToolReturn` |
| State fields | `<camelTool><PascalSetting>` | `lassoFeatherRadius` |
| State setters | `set<PascalTool><PascalSetting>` | `setLassoFeatherRadius` |

---

## Dos and don'ts

**Do**
- Keep all mouse/keyboard logic inside `use<Tool>Tool.ts`.
- Keep all Konva JSX inside `<Tool>Layer.tsx`.
- Let each hook manage its own global `pointerup` listener.
- Return `true`/`false` from `onMouseDown/Move/Up` to signal event consumption.
- Use React state for values that drive re-renders; use refs for values that
  only need to be read synchronously inside event handlers.

**Don't**
- Add tool logic directly to `CanvasStage.tsx` or `StageContent.tsx`.
- Put hooks or event handlers inside layer components.
- Share mutable refs across tool hooks.
- Add interaction code to `StageContent` — it is a rendering-only file.
