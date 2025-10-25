# AI Runner - Feature Implementation Roadmap

**Date Created:** October 23, 2025  
**Status:** Planning Phase  
**Estimated Timeline:** 8-12 weeks for full implementation

---

## 🎯 Overview

This document tracks the implementation of major new features for AI Runner, focusing on:
- Background service architecture
- Calendar and scheduling system
- Agent creation and management
- Web API and remote access
- Performance optimization
- Distribution improvements

---

## 🔥 CRITICAL FIXES (Do First)

- [x] **Universal Model Management System** ✅ COMPLETE
  - **Status:** Phase 1 & 2 complete - VRAM conflict prevention active
  - **Location:** `src/airunner/components/model_management/`
  - **Components:**
    - [x] HardwareProfiler - detects VRAM, RAM, compute capability
    - [x] QuantizationStrategy - auto-selects optimal quantization (6 levels)
    - [x] ModelRegistry - database of 8 models (Mistral, Llama, SD, TTS, STT)
    - [x] MemoryAllocator - manages VRAM/RAM allocation with pressure detection
    - [x] ModelResourceManager - central coordinator singleton with prepare/cleanup API
    - [x] Integration: LLMModelManager uses ModelResourceManager for load/unload
    - [x] Integration: QuantizationMixin uses HardwareProfiler
    - [x] Integration: SD managers have hardware_profiler property
    - [x] ModelSelectorWidget - UI for model selection with hardware compatibility
    - [x] **Phase 1: State Management** ✅
      - [x] ModelState enum (UNLOADED, LOADING, LOADED, UNLOADING, BUSY)
      - [x] CanvasMemoryTracker - tracks undo/redo history VRAM usage
      - [x] External VRAM detection (nvidia-smi/rocm-smi)
      - [x] can_perform_operation() validation method
      - [x] get_active_models() reporting method
      - [x] MemoryAllocationBreakdown - detailed memory analysis
    - [x] **Phase 2: GUI Integration & Legacy Removal** ✅
      - [x] Remove toggle_sd/unload_non_sd/load_non_sd signals
      - [x] GUI validation in stablediffusion_generator_form
      - [x] SD manager integration (prepare_model_loading/model_loaded/cleanup_model)
      - [x] Simplified LLM→SD workflow (no manual swapping)
    - [ ] **Phase 3: Canvas Integration** 🔄
      - [ ] Call update_canvas_history_allocation() from CustomScene
      - [ ] Trigger validation on undo/redo operations
      - [ ] Display memory warnings in canvas UI
    - [ ] **Phase 4: TTS/STT Integration**
      - [ ] Add ModelResourceManager calls to TTS manager
      - [ ] Add ModelResourceManager calls to STT manager
      - [ ] Test TTS+LLM+SD concurrent operation blocking
    - [ ] **Phase 5: UI Enhancements**
      - [ ] ModelStatusWidget - shows active models and memory
      - [ ] Automatic model swapping implementation
      - [ ] User settings: priority model, auto-unload timeout
  - **Documentation:** Full README.md with architecture, usage patterns, examples
  - **Current Status:** Users now see "Application Busy" popup if trying to generate art while LLM is loading

- [ ] **Restore Fine-Tuning System** 🔥 HIGH PRIORITY
  - **Goal:** Restore and modernize the fine-tuning capabilities that were previously removed
  - **Tasks:**
    - [ ] Search old commits for `fine_tuned_models` table schema (check `develop` branch)
    - [ ] Restore database schema: `fine_tuned_models` table with model metadata
    - [ ] Find and restore fine-tuning training code (LoRA, full fine-tuning support)
    - [ ] Update fine-tuning code to work with new LangChain/LangGraph system
    - [ ] Integrate with ModelRegistry (register fine-tuned models automatically)
    - [ ] Create fine-tuning manager component (handle training lifecycle)
    - [ ] Add fine-tuning UI tab (dataset selection, hyperparameters, progress)
    - [ ] Implement dataset management (upload, validation, preprocessing)
    - [ ] Add training progress monitoring (loss curves, checkpoints)
    - [ ] Support model export (HuggingFace format, quantized versions)
    - [ ] Write fine-tuning tests (mock training, parameter validation)
    - [ ] Document fine-tuning workflow in README

- [ ] **Docs tidy / wiki sync** 📚 MEDIUM PRIORITY
  - **Goal:** Clean up documentation and consolidate between docs/ and wiki
  - **Phase 1: Audit & Cleanup (docs/)**
    - [ ] List all files in `docs/` directory
    - [ ] Mark obsolete files for deletion (anything with "FIX", "PHASE", "TODO" in name)
    - [ ] Identify useful content that should be preserved
    - [ ] Extract reusable content from obsolete files before deletion
    - [ ] Delete obsolete files
  - **Phase 2: Wiki Content Migration**
    - [ ] Review all files in `/home/joe/Projects/airunner.wiki/`
    - [ ] Identify content to merge into `docs/` (architecture, dev guides)
    - [ ] Copy relevant content from wiki → `docs/` with proper formatting
    - [ ] Create index/navigation in `docs/README.md`
  - **Phase 3: Organization**
    - [ ] Organize `docs/` into subdirectories (architecture/, guides/, api/, migration/)
    - [ ] Update main README.md with links to documentation
    - [ ] Ensure all code READMEs link to relevant `docs/` pages
    - [ ] Remove duplicate content between wiki and `docs/`
  - **Final Structure:**
    - `docs/architecture/` - system design, component diagrams
    - `docs/guides/` - developer guides, contribution guide
    - `docs/api/` - API documentation, endpoint references
    - `docs/migration/` - upgrade guides, breaking changes

---

## �📋 Feature Categories

### Category A: Infrastructure & Architecture (Critical Path)
**Dependencies:** Required for many other features**Priority:** HIGHEST

- [ ] **A1: Background Service Architecture** ⚠️ BLOCKING - **HIGHEST PRIORITY**
  - **Goal:** Allow AI Runner to run as a background service/daemon
  - **Research Phase:**
    - [ ] Research Linux systemd service approach (auto-start, logging)
    - [ ] Research macOS LaunchAgent approach (plist, auto-start)
    - [ ] Research Windows service approach (NSSM, Task Scheduler)
    - [ ] Evaluate tray app vs. true daemon (user experience trade-offs)
    - [ ] Document pros/cons of each approach per platform
  - **Architecture Design:**
    - [ ] Design service lifecycle: start → ready → running → shutdown
    - [ ] Define IPC mechanism (Unix socket, named pipe, HTTP API)
    - [ ] Plan model persistence strategy (keep loaded vs. on-demand)
    - [ ] Design health check/heartbeat system
    - [ ] Plan logging strategy (separate log file, rotation)
  - **Implementation:**
    - [ ] Create ServiceManager component (`src/airunner/services/service_manager.py`)
    - [ ] Implement platform detection and service installer
    - [ ] Add service control CLI commands (start, stop, restart, status)
    - [ ] Create tray icon application (if using tray approach)
    - [ ] Implement graceful shutdown (save state, unload models)
    - [ ] Add startup configuration (which models to preload, API settings)
  - **Testing:**
    - [ ] Write unit tests for ServiceManager
    - [ ] Write integration tests (start/stop/restart cycles)
    - [ ] Test on Linux (systemd)
    - [ ] Test on macOS (LaunchAgent)
    - [ ] Test on Windows (if applicable)
  - **Documentation:**
    - [ ] Write installation guide per platform
    - [ ] Document service configuration options
    - [ ] Add troubleshooting section

- [ ] **A2: Web API Server** 🔥 HIGH PRIORITY (depends on A1)
  - **Goal:** Provide HTTP REST/WebSocket API for remote control
  - **Phase 1: Foundation**
    - [ ] Add FastAPI dependency to project
    - [ ] Create API application structure (`src/airunner/api/server.py`)
    - [ ] Set up CORS configuration (allow local network access)
    - [ ] Implement basic health check endpoint (`/health`)
    - [ ] Add API versioning strategy (`/v1/...`)
  - **Phase 2: LLM Endpoints**
    - [ ] POST `/v1/llm/chat` - streaming chat completion
    - [ ] POST `/v1/llm/completion` - non-streaming completion
    - [ ] GET `/v1/llm/models` - list available LLM models
    - [ ] POST `/v1/llm/load` - load specific LLM model
    - [ ] POST `/v1/llm/unload` - unload current LLM model
    - [ ] WebSocket `/v1/llm/stream` - streaming responses
  - **Phase 3: Art Generation Endpoints**
    - [ ] POST `/v1/art/generate` - start image generation
    - [ ] GET `/v1/art/status/{job_id}` - check generation status
    - [ ] GET `/v1/art/result/{job_id}` - get generated image
    - [ ] GET `/v1/art/models` - list available SD models
    - [ ] POST `/v1/art/load` - load specific SD model
    - [ ] DELETE `/v1/art/cancel/{job_id}` - cancel generation
  - **Phase 4: TTS/STT Endpoints**
    - [ ] POST `/v1/tts/synthesize` - text to speech
    - [ ] POST `/v1/stt/transcribe` - speech to text (upload audio)
    - [ ] GET `/v1/tts/models` - list TTS models
    - [ ] GET `/v1/stt/models` - list STT models
    - [ ] WebSocket `/v1/stt/stream` - real-time transcription
  - **Phase 5: Authentication & Security**
    - [ ] Implement API key generation/storage
    - [ ] Add API key authentication middleware
    - [ ] Add rate limiting per API key
    - [ ] Implement IP whitelist/blacklist
    - [ ] Add HTTPS support (self-signed cert option)
  - **Phase 6: Documentation**
    - [ ] Auto-generate OpenAPI/Swagger docs
    - [ ] Write API usage examples (curl, Python, JavaScript)
    - [ ] Document authentication flow
    - [ ] Add WebSocket usage examples
  - **Phase 7: Testing**
    - [ ] Write endpoint unit tests (pytest with TestClient)
    - [ ] Write WebSocket integration tests
    - [ ] Test concurrent request handling
    - [ ] Performance benchmark (requests/sec, latency)

- [ ] **A3: Model Lifecycle Management** 🔥 IN PROGRESS (builds on Universal Model Management)
  - **Phase 1: State Management & Resource Tracking** ⚠️ CRITICAL
    - [x] Use ModelResourceManager.prepare_model_loading() in LLMModelManager
    - [x] Use ModelResourceManager.cleanup_model() in LLMModelManager unload
    - [ ] Add ModelState enum (UNLOADED, LOADING, LOADED, UNLOADING, BUSY)
    - [ ] Implement state tracking in ModelResourceManager
    - [ ] Add canvas history memory allocation tracking
    - [ ] Track external app VRAM usage (optional: use nvidia-smi/rocm-smi)
    - [ ] Create allocation categories: models, canvas_history, system_reserve, external_apps
    - [ ] Implement can_perform_operation() validation before model loads
    - [ ] Add get_active_models() with real-time state reporting
  
  - **Phase 2: Remove Legacy Load/Unload System**
    - [ ] Audit and remove toggle_sd/unload_non_sd/load_non_sd signals
    - [ ] Replace manual LLM unload→SD load→SD unload→LLM load sequences
    - [ ] Implement automatic model swapping via ModelResourceManager
    - [ ] Remove prevent_unload_on_llm_image_generation setting (obsolete)
    - [ ] Centralize all model state transitions through ModelResourceManager
  
  - **Phase 3: GUI Integration**
    - [ ] Add request validation at GUI level (generate button, chat input)
    - [ ] Show "Application Busy" dialog when resources unavailable
    - [ ] Create ModelStatusWidget for home tab (real-time VRAM/model display)
    - [ ] Integrate ModelSelectorWidget into LLM settings tab UI
    - [ ] Add progress indicators for model state transitions
    - [ ] Display allocation breakdown (models vs canvas vs system)
  
  - **Phase 4: SD/TTS/STT Integration**
    - [ ] Integrate ModelResourceManager with BaseDiffusersModelManager.load()
    - [ ] Integrate ModelResourceManager with TTS managers
    - [ ] Integrate ModelResourceManager with STT managers
    - [ ] Add model metadata to ModelRegistry (SDXL, SD1.5, Whisper, Bark)
    - [ ] Implement automatic quantization selection for SD models
  
  - **Phase 5: Advanced Features**
    - [ ] Implement timeout-based model cleanup (Ollama-style: unload after N minutes)
    - [ ] Create model warmup/preload strategies for frequently-used models
    - [ ] Add memory pressure callbacks to trigger automatic unloads
    - [ ] Optimize model loading order based on priority/frequency
    - [ ] Write performance benchmarks (load time, memory overhead)
    - [ ] Add telemetry for model usage patterns
  
  - **Testing**
    - [ ] Test: LLM loading → art request → see "busy" popup
    - [ ] Test: SD loading → chat request → see "busy" popup
    - [ ] Test: LLM image tool auto-swaps models without manual unload/load
    - [ ] Test: Canvas history memory is tracked and prevents OOM
    - [ ] Test: Status widget updates in real-time
    - [ ] Test: Model states transition correctly (LOADING→LOADED→BUSY→LOADED→UNLOADING→UNLOADED)

### Category B: Agent System Enhancements
**Priority:** HIGH

- [ ] **B1: Agent Creation Tools (LLM)**
  - Create `create_agent` tool
  - Create `configure_agent` tool
  - Create `list_agents` tool
  - Create `delete_agent` tool
  - Create `run_agent` tool
  - Add agent templates system
  - Write agent creation tests

- [ ] **B2: Custom Agent Widget (GUI)**
  - Design agent creation UI mockup
  - Implement agent configuration form
  - Add agent template selector
  - Create agent testing interface
  - Integrate with agent tools
  - Write UI tests

- [ ] **B3: Expert Agent System**
  - Design agent specialization architecture
  - Implement tool-specific agents
  - Create agent routing system
  - Add agent result aggregation
  - Integrate with nodegraph
  - Write integration tests

### Category C: Calendar & Scheduling
**Priority:** MEDIUM-HIGH

- [ ] **C1: Calendar Data Model**
  - Design calendar/event database schema
  - Create Event, Reminder, RecurringEvent models
  - Implement iCal import/export
  - Add Calendly integration hooks
  - Write data model tests

- [ ] **C2: Calendar LLM Tools**
  - Create `create_event` tool
  - Create `list_events` tool
  - Create `update_event` tool
  - Create `delete_event` tool
  - Create `create_reminder` tool
  - Create `schedule_recurring_event` tool
  - Write calendar tool tests

- [ ] **C3: Calendar GUI Tab**
  - Design calendar UI mockup (week/month/year views)
  - Implement calendar widget with Qt
  - Add event creation/editing dialogs
  - Implement drag-and-drop scheduling
  - Add calendar sync features
  - Write calendar UI tests

### Category D: Nodegraph Control
**Priority:** MEDIUM

- [ ] **D1: Nodegraph LLM Tools**
  - Create `create_workflow` tool
  - Create `list_workflows` tool
  - Create `modify_workflow` tool
  - Create `execute_workflow` tool
  - Create `switch_mode` tool (AI Runner ↔ LangGraph)
  - Add node creation/connection tools
  - Write nodegraph tool tests

- [ ] **D2: Workflow Templates**
  - Create common workflow templates
  - Implement template system
  - Add template discovery
  - Document workflow patterns
  - Write template tests

### Category E: UI/UX Improvements
**Priority:** MEDIUM

- [ ] **E1: Provider/Model Selection UI**
  - Design VSCode-style model selector
  - Implement dropdown with search
  - Create "Manage Models" dialog
  - Add provider configuration UI
  - Integrate with settings
  - Write UI tests

- [ ] **E2: Settings Enhancements**
  - Add "Run in Background" toggle
  - Add "Start at Login" toggle
  - Create service configuration panel
  - Add API server settings
  - Update settings persistence
  - Write settings tests

### Category F: Remote Access & Web Client
**Priority:** MEDIUM

- [ ] **F1: React Web Client** (Separate Repository)
  - Initialize Vite + React project
  - Design responsive UI for tablet
  - Implement LLM chat interface
  - Add art generation interface
  - Add TTS/STT controls
  - Create build/deployment scripts

- [ ] **F2: API Documentation**
  - Write comprehensive API docs
  - Create usage examples
  - Add security best practices
  - Document WebSocket protocols
  - Create client libraries (optional)

### Category G: Testing & Quality
**Priority:** HIGH

- [ ] **G1: Evaluation Tests**
  - Port eval test framework from /agent
  - Create test datasets for main LLM
  - Implement RAG accuracy tests
  - Add tool execution tests
  - Set up automated eval runs
  - Write eval reports

- [ ] **G2: GUI Automation**
  - Research Qt testing frameworks
  - Implement automated UI tests
  - Add screenshot comparison tests
  - Create test data generators
  - Set up CI for GUI tests

### Category H: Performance & Optimization
**Priority:** HIGH

- [ ] **H1: Performance Investigation**
  - Benchmark current LLM performance
  - Compare with Ollama (llama3.2)
  - Profile inference pipeline
  - Identify bottlenecks
  - Test different quantizations
  - Document findings

- [ ] **H2: Performance Improvements**
  - Optimize model loading
  - Improve inference speed
  - Reduce memory footprint
  - Add caching strategies
  - Benchmark improvements
  - Write performance tests

### Category I: Distribution & Deployment
**Priority:** MEDIUM

- [ ] **I1: Snap Package**
  - Update snapcraft.yaml
  - Test snap build process
  - Add snap-specific configs
  - Submit to Snap Store
  - Document snap installation
  - Write snap tests

- [ ] **I2: Installation Improvements**
  - Create installation wizard
  - Add dependency management
  - Improve error handling
  - Add post-install setup
  - Document installation process

### Category J: Tool System Enhancements
**Priority:** LOW-MEDIUM

- [ ] **J1: Tool Pagination**
  - Research LangChain/LangGraph pagination
  - Implement tool pagination if needed
  - Add tool search/filter
  - Optimize tool loading
  - Write pagination tests

### Category K: Documentation & Cleanup
**Priority:** HIGH (for commit)

- [x] **K1: Markdown Cleanup** ✅
  - Review all markdown files
  - Extract useful information
  - Update main README.md
  - Create COMMIT_MESSAGE.md
  - Remove obsolete files
  - Organize documentation

---

## 🔄 Implementation Phases

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Establish infrastructure for advanced features

1. **A1: Background Service Architecture** (Week 1)
   - Research and design
   - Implement basic service
   - Add configuration options

2. **A3: Model Lifecycle Management** (Week 2)
   - Implement loading/unloading
   - Add timeout cleanup
   - Optimize memory usage

3. **A2: Web API Server** (Week 3)
   - Set up FastAPI
   - Create basic endpoints
   - Add authentication

### Phase 2: Agent System (Weeks 4-5)
**Goal:** Enable agent creation and management

1. **B1: Agent Creation Tools** (Week 4)
   - Implement LLM tools
   - Add templates
   - Write tests

2. **B2: Custom Agent Widget** (Week 5)
   - Design and implement UI
   - Integrate with tools
   - Add agent testing

### Phase 3: Calendar & Scheduling (Weeks 6-7)
**Goal:** Complete calendar system

1. **C1: Calendar Data Model** (Week 6)
   - Database schema
   - iCal integration
   - Tests

2. **C2: Calendar LLM Tools** (Week 6)
   - Implement tools
   - Write tests

3. **C3: Calendar GUI Tab** (Week 7)
   - UI implementation
   - Event management
   - Tests

### Phase 4: Advanced Features (Weeks 8-10)
**Goal:** Add nodegraph control, remote access, performance

1. **D1: Nodegraph LLM Tools** (Week 8)
2. **F1: React Web Client** (Week 9)
3. **H1 & H2: Performance** (Week 10)

### Phase 5: Polish & Deploy (Weeks 11-12)
**Goal:** Testing, documentation, distribution

1. **G1: Evaluation Tests** (Week 11)
2. **I1: Snap Package** (Week 11)
3. **E1: UI Improvements** (Week 12)
4. **Documentation & Testing** (Week 12)

---

## 📝 Implementation Notes

### Background Service Design Options

**Option 1: System Service (Linux systemd)**
- Pros: True background process, survives logout, controlled startup
- Cons: Requires root/admin, complex venv activation, platform-specific

**Option 2: System Tray Application**
- Pros: User-level, easy to implement, cross-platform
- Cons: Requires user login, less "background-like"

**Option 3: Hybrid Approach** ⭐ RECOMMENDED
- Service for model management and API
- Tray app for user interaction
- Service can run independently or be launched by tray app

### API Architecture

```
FastAPI Server
├── /api/v1/llm
│   ├── /chat (POST, WebSocket)
│   ├── /models (GET, POST)
│   └── /history (GET)
├── /api/v1/art
│   ├── /generate (POST)
│   ├── /models (GET)
│   └── /gallery (GET)
├── /api/v1/tts
│   └── /speak (POST)
└── /api/v1/stt
    └── /transcribe (POST)
```

### Agent System Architecture

```
AgentManager
├── create_agent(config) -> Agent
├── load_agent(id) -> Agent
├── list_agents() -> List[Agent]
└── delete_agent(id) -> bool

Agent
├── id: str
├── name: str
├── config: AgentConfig
├── specialized_tools: List[Tool]
├── execute(input) -> Response
└── can_handle(tool_call) -> bool
```

---

## 🧪 Testing Strategy

### Unit Tests
- All new tools (agent, calendar, nodegraph)
- Service management components
- API endpoints
- Agent creation/management

### Integration Tests
- Agent workflow execution
- Calendar + scheduling integration
- API + frontend integration
- Background service operations

### Evaluation Tests
- LLM response quality
- RAG accuracy
- Tool execution success rate
- Performance benchmarks

### GUI Tests
- Calendar UI interactions
- Agent creation workflow
- Settings modifications
- Model selection UI

---

## 🎯 Success Criteria

### Phase 1 Complete When:
- [ ] Background service runs and manages models
- [ ] API server responds to basic requests
- [ ] Models load/unload intelligently
- [ ] All tests pass

### Phase 2 Complete When:
- [ ] LLM can create/manage agents
- [ ] GUI allows custom agent creation
- [ ] Agents can be specialized for tools
- [ ] All tests pass

### Phase 3 Complete When:
- [ ] Calendar system stores/retrieves events
- [ ] LLM can manage calendar
- [ ] GUI provides full calendar functionality
- [ ] All tests pass

### Phase 4 Complete When:
- [ ] Nodegraph tools fully functional
- [ ] Web client can access AI Runner
- [ ] Performance matches or exceeds Ollama
- [ ] All tests pass

### Phase 5 Complete When:
- [ ] Snap package installs correctly
- [ ] Eval tests provide quality metrics
- [ ] UI improvements complete
- [ ] Documentation comprehensive
- [ ] All tests pass

---

## 📚 References

- LangChain Tool Documentation
- FastAPI Best Practices
- Qt Calendar Widget Examples
- systemd Service Configuration
- Snap Package Guidelines
- React + Vite Setup Guides

---

## 🔗 Related Documents

- [Main README](../README.md)
- [Architecture Documentation](OVERVIEW.md)
- [API Documentation](docs/API.md) (to be created)
- [Agent System Guide](docs/AGENT_SYSTEM.md) (to be created)

---

**Last Updated:** October 23, 2025  
**Next Review:** Start of each implementation phase
