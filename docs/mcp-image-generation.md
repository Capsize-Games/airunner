# MCP Image Generation

Stdio [Model Context Protocol](https://modelcontextprotocol.io) server
that exposes AI Runner image generation (Z-Image Turbo by default) to
MCP hosts such as Claude Desktop, Muse, or any MCP client.

## Architecture

`airunner-mcp` is a thin client over the daemon's public art HTTP API —
it carries no model weights and needs no GPU. The daemon keeps doing
the heavy lifting: Z-Image/SD pipelines, content-safety gates,
capacity admission, and PNG export.

```text
MCP host --stdio--> airunner-mcp --HTTP--> daemon :8188
                                    POST /api/v1/art/generate
                                    GET  /api/v1/art/status/{job}
                                    GET  /api/v1/art/result/{job}/{index}
                                    DELETE /api/v1/art/cancel/{job}
                                    GET  /api/v1/art/models[/registry]
                                    POST /api/v1/art/remove-background
```

There is no local MCP runtime before this: the only prior tools were
the in-LLM `generate_image` LangChain tool and the HTTP routes above.
This server bridges them for external agents.

## Install

From this repository:

```bash
uv pip install -e "./services[mcp]"
```

The server starts a local daemon on demand: when the first tool
call finds no daemon listening on a loopback `AIRUNNER_DAEMON_URL`,
it launches one (the same `airunner-daemon` the GUI supervises) and
waits for its health endpoint before issuing the art call. A daemon
that is already running is used as-is and never relaunched. If you
prefer to manage the daemon yourself, start it first (it serves the
art API on loopback by default), then register the server:

```json
{
  "mcpServers": {
    "airunner-image": {
      "command": "airunner-mcp",
      "env": {
        "AIRUNNER_DAEMON_URL": "http://127.0.0.1:8188",
        "AIRUNNER_MCP_OUTPUT_DIR": "~/.local/share/airunner/mcp-images"
      }
    }
  }
}
```

(`python -m airunner_services.mcp` runs the same server without the
console script.)

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `AIRUNNER_DAEMON_URL` | `http://127.0.0.1:8188` | Daemon base URL |
| `AIRUNNER_API_KEY` | _(empty)_ | Bearer token; needed only for non-loopback binds |
| `AIRUNNER_MCP_OUTPUT_DIR` | `~/.local/share/airunner/mcp-images` | Where finished PNGs are saved |
| `AIRUNNER_MCP_GENERATION_TIMEOUT_S` | `600` | Block limit for one `generate_image` call |
| `AIRUNNER_MCP_POLL_INTERVAL_S` | `2` | Status poll cadence while waiting |
| `AIRUNNER_MCP_REQUEST_TIMEOUT_S` | `30` | Per-request HTTP timeout |
| `AIRUNNER_MCP_AUTO_START_DAEMON` | `1` | Start a local daemon when none is listening (loopback URLs only) |
| `AIRUNNER_MCP_DAEMON_STARTUP_TIMEOUT_S` | `90` | Wait limit for an auto-started daemon to report healthy |

## Tools

| Tool | Behavior |
| --- | --- |
| `generate_image` | Start a job, wait for completion, save PNGs, return a summary plus the images |
| `get_generation_status` | Poll progress/state for one job id |
| `fetch_generation_result` | Download one finished batch image by index |
| `cancel_generation` | Cancel a running job (best-effort) |
| `list_image_models` | Installed models and registry entries for `model`/`version`/`scheduler` input |
| `remove_background` | Remove the background from one input image (RMBG-2.0), save the PNG, return it |

`remove_background` takes an `input_image_path`, posts it to
`POST /api/v1/art/remove-background`, and saves the RGBA result as
`<name>-nobg.png` under the output dir. It is synchronous — no job
polling — and the same input-image screening applies.

Defaults target Z-Image Turbo: one detailed prompt, guidance
(`cfg_scale`) `0.0`, ~9 steps. Negative prompts are accepted by the
schema but Z-Image ignores them — put everything in `prompt`.

`provider` defaults to `"local"` so prompts stay on the host. Passing
`"muse"` sends the prompt (and any input image) to Meta; there is no
silent fallback either way. See [art-providers](art-providers.md).

## Safety

Input validation (prompt length, dimensions, steps, seed, job-id
shape) fails locally before any HTTP side effect; the daemon
re-validates and its content-safety gate still screens every prompt
and input image. Error text never carries prompts or keys.
