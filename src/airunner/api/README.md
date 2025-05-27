# airunner.api

This directory contains the core API service layer for the AI Runner application. It provides a modular, signal-based interface for interacting with various AI and multimedia services, decoupling business logic from the GUI and application lifecycle.

## Overview

- **api.py**: Main singleton API class, tightly integrated with the application and GUI. Use this when you need full app and signal integration.
- **api_manager.py**: Lightweight, decoupled manager for API services. Use this in headless, worker, or test contexts where GUI/app logic is not needed.
- **api_service_base.py**: Base class for all API services, providing signal emission and settings integration.

## Service Modules
Each service module provides a class for interacting with a specific domain via signals:

- **art_services.py**: Stable Diffusion and image generation workflows.
- **canvas_services.py**: Canvas/grid/image editing and manipulation.
- **chatbot_services.py**: Chatbot mood and interaction signals.
- **embedding_services.py**: Embedding management and status updates.
- **image_filter_services.py**: Image filter application and preview.
- **llm_services.py**: Large Language Model (LLM) requests, chat, and RAG operations.
- **lora_services.py**: LoRA (Low-Rank Adaptation) model management.
- **nodegraph_services.py**: Node graph workflow execution and management.
- **stt_services.py**: Speech-to-text (STT) processing.
- **tts_services.py**: Text-to-speech (TTS) playback and control.
- **video_services.py**: Video generation and progress updates.

## Usage

- **For full application integration:**
  ```python
  from airunner.api import API
  api = API()
  api.llm.send_request(prompt="Hello!")
  ```
- **For decoupled/service-only usage:**
  ```python
  from airunner.api.api_manager import APIManager
  api_manager = APIManager(emit_signal=None)
  api_manager.tts.play_audio("Hello!")
  ```

## Testing

Unit tests for all services are provided in the `test/` subdirectory. These use `pytest` and `unittest.mock` to verify signal emission and service logic.

## Extending

To add a new service:
1. Create a new `*_services.py` file, subclassing `APIServiceBase`.
2. Implement methods that emit signals for your domain.
3. Add your service to `api.py` and `api_manager.py` as needed.
4. Write unit tests in `test/`.

## Notes
- All services use Qt signals for communication, enabling loose coupling between UI, backend, and worker processes.
- The `emit_signal` function is injected for flexibility and testability.

---
For more details, see the main project README and the documentation in `docs/`.
