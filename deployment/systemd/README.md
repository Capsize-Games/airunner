# AI Runner Headless Server Deployment

This directory contains configuration files for deploying AI Runner headless server as a system service.

## Systemd Service Setup (Ubuntu/Debian)

The `airunner-headless.service` file allows AI Runner to run as a background service that starts automatically at system boot.

### Installation Steps

1. **Copy the service file to systemd directory:**
   ```bash
   sudo cp deployment/systemd/airunner-headless.service /etc/systemd/system/
   ```

2. **Edit the service file if needed:**
   ```bash
   sudo nano /etc/systemd/system/airunner-headless.service
   ```
   
   Update these values if your paths are different:
   - `User=joe` - Change to your username
   - `Group=joe` - Change to your group
   - `WorkingDirectory=/home/joe/Projects/airunner` - Change to your AI Runner path
   - `ExecStart=/home/joe/Projects/airunner/.venv/bin/python` - Change to your Python path

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
2. Verify Python path: `which python` in your virtual environment
3. Verify working directory exists and has correct permissions
4. Test manually: `cd /home/joe/Projects/airunner && .venv/bin/python -m airunner.main`

**Permission issues:**
```bash
# Ensure user 'joe' can access AI Runner directory
sudo chown -R joe:joe /home/joe/Projects/airunner

# Check if user can write to logs
ls -la /home/joe/Projects/airunner/
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
- **Process priority:** Set to -5 (slightly higher priority)
- **Logging:** All output goes to systemd journal

### Environment Variables

The service sets these environment variables:
- `AIRUNNER_HEADLESS=1` - Run in headless mode (no GUI)
- `AIRUNNER_LLM_ON=1` - Enable LLM service
- `PATH` - Includes virtual environment Python

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
cd /home/joe/Projects/airunner/booksite
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
