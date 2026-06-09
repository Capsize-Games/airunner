# AI Runner Web Client

The web-based GUI for AI Runner, built with React, TypeScript, and Vite.

## Overview

This is the user-facing web GUI that connects to the AI Runner daemon API.
It provides:

- **AI Companion Chat** — conversation interface with a configurable AI
  companion with personality, mood, and memory
- **AI Art Canvas** — layered drawing and generation surface with SDXL and
  Z-Image Turbo support
- **Settings** — configuration for LLM, TTS, STT, art models, and more
- **Model Management** — built-in HuggingFace and CivitAI downloaders
- **Knowledge Base** — document upload and RAG-based retrieval

## Development

### Prerequisites

- Node.js 18+ and npm
- The AI Runner daemon running on port 8188

### Getting Started

```bash
cd client
npm install
npm run dev
```

The dev server starts on `http://localhost:5173` and proxies API requests to
the daemon at `http://localhost:8188`.

### Building for Production

```bash
npm run build
```

Output is written to `dist/`.

## Architecture

The web client communicates with the AI Runner daemon via REST API
(`/api/v1/*`). It does not run any AI models directly — all LLM, image
generation, TTS, and STT workloads are handled by the daemon and its
managed runtimes.

## Using Icons

Icons come from [lucide-react](https://lucide.dev/icons/) (v1.17+).
**Never write inline `<svg>` tags** — always use a lucide component.

Two patterns are available:

### Static import (preferred)

Import the component directly from `lucide-react` when the icon is
known at build time:

```tsx
import { LassoSelect, SquareDashed, Brush } from "lucide-react";
// …
<LassoSelect size={14} strokeWidth={1.75} />
```

### Dynamic / string-based lookup

When the icon name must be resolved at runtime (e.g. driven by
configuration), use the [`LucideIcon`](client/src/components/shared/LucideIcon.tsx)
wrapper which maps kebab-case strings to lucide components:

```tsx
import LucideIcon from "@/components/shared/LucideIcon";
// …
<LucideIcon name="bot-message-square" size={16} />
```

If the icon you need is not yet registered in [`LucideIcon`](client/src/components/shared/LucideIcon.tsx),
add both the import and the map entry.

## Project Structure

- `src/` — TypeScript/React source files
  - `api/` — API client modules
  - `components/` — React components organized by feature
  - `features/` — feature-oriented modules (canvas, LLM, TTS)
  - `styles/` — SCSS stylesheets
  - `types/` — TypeScript type definitions
- `public/` — Static assets and icon files

## Canvas Tools

The canvas uses a composable tool system. See
[`CANVAS_TOOL_PATTERN.md`](client/src/features/canvas/CANVAS_TOOL_PATTERN.md)
for the architecture, conventions, and how to add a new tool.
