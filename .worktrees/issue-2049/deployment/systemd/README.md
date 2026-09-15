# AI Runner Headless Server Deployment

This directory contains configuration files for deploying AI Runner headless
server as a Linux system service.

The packaged `airunner-headless.service` file is a relocatable template. Use
`deployment/systemd/install.sh` to render it with the actual bundle root,
Python executable, and runtime data directories for the current install.

This surface is primarily for the `distributed` daemon install mode. The
normal entry point is:

```bash
./deployment/install_distributed.sh --role daemon --systemd
```

That command creates the daemon venv first, then calls this renderer with the
resolved install root and Python path. Invoke `deployment/systemd/install.sh`
directly only when you are manually rendering the service for a bundle or a
custom venv layout.

## Install Layout

Linux desktop bundles and distributed daemon installs are expected to keep the
AIRunner install root separate from the writable runtime data root.

- Install root: the installed application directory, for example
   `~/.local/airunner`, `~/.local/airunner/distributed/daemon`, or
   `/opt/airunner`
- Install Python: one of `<install>/venv/bin/python`,
   `<install>/.venv/bin/python`, or `<install>/bin/python`
- Runtime data root: `~/.local/share/airunner` unless `AIRUNNER_DATA_DIR`
   overrides it
- Runtime configs: `<data>/runtime/configs`
- Runtime logs: `<data>/runtime/logs`
- Runtime sockets: `<data>/runtime/sockets`
- Runtime cache: `<data>/cache`
- Models: `<data>/models`

The desktop launchers created by the top-level installer export
`AIRUNNER_BUNDLE_ROOT`, `AIRUNNER_PYTHON`, and the standardized runtime
directory variables so the daemon and sidecars can discover the bundle and
runtime roots predictably after relocation.

The distributed daemon installer passes the same resolved install root and
Python path through `AIRUNNER_INSTALL_ROOT`, `AIRUNNER_TEMPLATE_ROOT`, and
`AIRUNNER_PYTHON` before this renderer writes the systemd unit.

## Systemd Service Setup (Ubuntu/Debian)

The rendered `airunner-headless.service` file allows AI Runner to run as a
background service that starts automatically at system boot.

### Installation Steps

1. **Render and install the service template:**
   ```bash
   sudo bash deployment/systemd/install.sh
   ```

2. **Optional overrides before rendering:**
   - `AIRUNNER_BUNDLE_ROOT=/path/to/bundle`
   - `AIRUNNER_PYTHON=/path/to/python`
   - `AIRUNNER_DATA_DIR=/path/to/runtime-data`

3. **Reload systemd to recognize the new service:**
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable the service to start at boot:**
   ```bash
   sudo systemctl enable airunner-headless
   ```

5. **Start the service:**
   ```bash
   sudo systemctl start airunner-headless
   ```

### Service Management

**Check service status:**
```bash
sudo systemctl status airunner-headless
```

**View service logs:**
```bash
# View recent logs
sudo journalctl -u airunner-headless -n 100

# Follow logs in real-time
sudo journalctl -u airunner-headless -f

# View logs since last boot
sudo journalctl -u airunner-headless -b
```

**Stop the service:**
```bash
sudo systemctl stop airunner-headless
```

**Restart the service:**
```bash
sudo systemctl restart airunner-headless
```

**Disable auto-start at boot:**
```bash
sudo systemctl disable airunner-headless
```

**Reload service after editing config:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart airunner-headless
```

### Troubleshooting

**Service fails to start:**
1. Check logs: `sudo journalctl -u airunner-headless -n 100`
2. Verify the rendered Python path exists under your bundle root
3. Verify the runtime data directory exists and has correct permissions
4. Test manually from the bundle root with the rendered Python path

**Permission issues:**
```bash
# Ensure the service user can access the runtime data directory
sudo chown -R airunner:airunner ~/.local/share/airunner

# Check if user can write to runtime logs
ls -la ~/.local/share/airunner/runtime/
```

**Service won't stop:**
```bash
# Force stop
sudo systemctl kill airunner-headless

# Check for lingering processes
ps aux | grep airunner
```

### Configuration

The service is configured with:
- **Auto-restart:** Service will automatically restart if it crashes
- **Restart delay:** 10 seconds between restart attempts
- **File limits:** Increased to 65536 for handling many connections
- **Local-only bind defaults:** The packaged unit binds the daemon to `127.0.0.1`
- **Runtime directories:** Runtime config, logs, sockets, cache, and model roots live under `~/.local/share/airunner`
- **Sandboxing:** The service uses `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`, `ProtectHome=read-only`, and a restricted writable path
- **Logging:** By default the daemon logs to stdout/stderr only, so systemd captures everything in `journalctl`; runtime log files under `~/.local/share/airunner/runtime/logs` are only written when `AIRUNNER_SAVE_LOG_TO_FILE=1`

### Environment Variables

The service sets these environment variables:
- `AIRUNNER_HEADLESS=1` - Run in headless mode (no GUI)
- `AIRUNNER_LLM_ON=1` - Enable LLM service
- `AIRUNNER_RUNTIME_BIND_HOST=127.0.0.1` - Keep managed runtimes on loopback by default
- `AIRUNNER_BUNDLE_ROOT` - Resolved install root for the rendered bundle
- `AIRUNNER_PYTHON` - Resolved bundle Python executable
- `AIRUNNER_DAEMON_CONFIG` - Standard daemon config path
- `PATH` - Prefers the rendered bundle's `bin` directory

The standardized runtime layout is:
- `~/.local/share/airunner/runtime/configs` for daemon and sidecar config files
- `~/.local/share/airunner/runtime/logs` for daemon and sidecar logs
- `~/.local/share/airunner/runtime/sockets` for local socket-style discovery paths
- `~/.local/share/airunner/cache` for runtime-owned caches
- `~/.local/share/airunner/models` for default model storage

To add more environment variables, edit the service file and add lines like:
```ini
Environment="YOUR_VAR=value"
```

### Testing the HTTP Server

Once the service is running, test it:

```bash
# Health check
curl http://localhost:8080/health

# Test LLM endpoint
curl -X POST http://localhost:8080/llm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello",
    "action": "CHAT",
    "stream": false,
    "llm_request": {
      "max_new_tokens": 50
    }
  }'
```

### Integration with BookSite

Once the service is running, you can use the BookSite classification:

```bash
cd /path/to/airunner/booksite
./manage.py ai_process_books --books 535
```

The Django app will automatically connect to `http://localhost:8080` and use the RAG tools.

## Uninstallation

To remove the service:

```bash
# Stop and disable
sudo systemctl stop airunner-headless
sudo systemctl disable airunner-headless

# Remove service file
sudo rm /etc/systemd/system/airunner-headless.service

# Reload systemd
sudo systemctl daemon-reload
```
