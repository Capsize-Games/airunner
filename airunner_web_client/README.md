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
cd airunner_web_client
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

## Project Structure

- `src/` — TypeScript/React source files
  - `api/` — API client modules
  - `components/` — React components organized by feature
  - `styles/` — SCSS stylesheets
  - `types/` — TypeScript type definitions
- `public/` — Static assets and icon files
