# Docker — Local Development (open-core)

This is the **development** stack: PostgreSQL + the AI Runner server, with the
full local ML stack available so GPU features work in Docker just like
bare-metal. Production deployment lives separately (private; see the extensions
repo) so this open-core repo never ships production topology or secrets.

## Prerequisites

- Docker Engine + Compose v2 (`docker compose version`)
- For GPU: the NVIDIA driver + [nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit).
  No CUDA base image is needed — torch's Linux wheels bundle the CUDA runtime.

## Quick start

```bash
cp .env.docker.example .env      # then edit secrets/keys
./scripts/docker.sh up           # auto-detects GPU; CPU otherwise
./scripts/docker.sh up --client  # also start the Vite dev server (:5173)
./scripts/docker.sh logs server
```

The API is on http://localhost:8080. Source is bind-mounted, so edits to
`server/`, `extensions/`, and `client/` are picked up live.

## What runs

| Service  | Image / build            | Purpose                                  |
|----------|--------------------------|------------------------------------------|
| `db`     | `postgres:16`            | Multi-tenant database (per-user schemas) |
| `server` | `docker/Dockerfile`      | API server (`airunner-server`)           |
| `client` | `node:22` (profile)      | Vite dev server                          |

## GPU

`./scripts/docker.sh` adds `docker-compose.gpu.yml` automatically when it sees
an NVIDIA GPU **and** Docker can reach it. To do it manually, or force on/off:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up   # force GPU
AIRUNNER_NO_GPU=1 ./scripts/docker.sh up                            # force CPU
```

GPU passthrough has **two** host requirements — the wrapper checks both:

1. **NVIDIA driver loaded.** Detected via `nvidia-smi`, `/dev/nvidia0`, or
   `/proc/driver/nvidia/version` (so it works even when `nvidia-smi` isn't on
   PATH, as with open-kernel-module installs).
2. **`nvidia-container-toolkit` installed and registered with Docker** — this is
   what actually lets a container see the GPU. Without it the wrapper prints a
   warning and runs on CPU (the GPU override would otherwise fail with
   *"could not select device driver nvidia"*).

Install the toolkit once on the host (Debian/Ubuntu):

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
```

For systemd:

```bash
sudo systemctl restart docker
```

For sysvinit:

```bash
sudo service docker restart
```

Verify the daemon now exposes the runtime, then start the stack:

```bash
docker info | grep -i nvidia          # expect: Runtimes: ... nvidia ...
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi  # smoke test
./scripts/docker.sh up                # now auto-enables the GPU override
```

When the GPU is live, `HardwareProfiler` reports a non-zero `total_vram_gb` and
the site footer's hardware stats appear (they're hidden when VRAM reads 0).

For a lighter, API-only image without torch, build with `AIRUNNER_DOCKER_EXTRAS=core`.

## Extensions & the open-core boundary

`extensions/` is a **separate private repo** checked out inside this tree. It is
excluded from the image (`.dockerignore`) and instead **bind-mounted** at
runtime and enabled via `AIRUNNER_EXTENSIONS` in your `.env`. No private code is
ever baked into an image built from this repo.

## Common tasks

```bash
./scripts/docker.sh migrate   # apply migrations (core + extensions)
./scripts/docker.sh shell     # bash in the server container
./scripts/docker.sh psql      # psql into the database
./scripts/docker.sh down      # stop everything (data volumes persist)
docker compose down -v        # also delete the database volume
```

## Notes

- Migrations run automatically on server boot (and via the `migrate` task).
- `AIRUNNER_REQUIRE_POSTGRES=1` is set for containers — the server refuses to
  fall back to SQLite, matching production.
- The Hugging Face cache is mounted from `HF_HOME` so models aren't
  re-downloaded on every rebuild.
