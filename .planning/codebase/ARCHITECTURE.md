<!-- refreshed: 2026-06-17 -->
# Architecture

**Analysis Date:** 2026-06-17

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js 14 App Router)                    │
│  `frontend/app/page.tsx`                                                     │
│                                                                              │
│  UrlInput  →  ModelSelector  →  JobStatus  →  VideoPlayer                   │
│  `components/UrlInput.tsx`    `components/JobStatus.tsx`                    │
│  `components/ModelSelector.tsx`  `components/VideoPlayer.tsx`               │
└────────────────────┬────────────────────────────────────────────────────────┘
         REST (fetch) │                     ▲ Socket.IO events
         POST /jobs   │                     │ job:progress / job:done / job:error
                      ▼                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Backend — FastAPI + Socket.IO (ASGI)                      │
│  `backend/app/main.py`  ←→  `backend/app/socket.py`                        │
│                                                                              │
│  Routers: /jobs  /models  /domains                                          │
│  `backend/app/routers/jobs.py`                                              │
│          │                                                                   │
│          ▼  BackgroundTask                                                   │
│  Pipeline Orchestrator                                                       │
│  `backend/app/pipeline.py`                                                  │
│          │                                                                   │
│   ┌──────┴──────────────────────────────────────────┐                      │
│   │  Step 1: Download        Step 2: Transcribe      │                      │
│   │  `services/downloader.py`  `services/transcriber.py`                   │
│   │  Step 3: Translate       Step 4: Subtitle        │                      │
│   │  `services/translator.py`  `services/subtitle.py`                      │
│   └──────────────────────────────────────────────────┘                      │
│                                                                              │
│  Data: SQLite via SQLModel  `backend/app/models/`                           │
│  Static files: `{storage_path}/{job_id}/`                                   │
└────────────────┬──────────────────────────────────────────────────────────-─┘
                 │  HTTPS (base64 audio)
                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GPU Workers (RunPod Serverless / API)                     │
│                                                                              │
│  STT Worker: faster-whisper on CUDA                                         │
│  `backend/workers/stt_worker/handler.py`                                    │
│                                                                              │
│  Translation: Qwen-MT API (DashScope) / NLLB worker endpoint               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | HTTP routing, CORS, static file serving, startup | `backend/app/main.py` |
| Socket.IO server | Real-time job progress emission to browser clients | `backend/app/socket.py` |
| Jobs router | POST /jobs (create + enqueue), GET /jobs/{id}, GET /jobs | `backend/app/routers/jobs.py` |
| Models router | GET /models — available STT model registry | `backend/app/routers/models.py` |
| Domains router | GET /domains — available translation domain configs | `backend/app/routers/domains.py` |
| Pipeline orchestrator | Sequences download → transcribe → translate → subtitle steps | `backend/app/pipeline.py` |
| Downloader service | yt-dlp audio/video download + FFmpeg audio extraction | `backend/app/services/downloader.py` |
| Transcriber service | Protocol abstraction over STT backends (mock/local/RunPod/GPT-4o) | `backend/app/services/transcriber.py` |
| Translator service | Protocol abstraction over translation backends (mock/Qwen-MT/NLLB) | `backend/app/services/translator.py` |
| Subtitle service | SRT and WebVTT file generation from timestamped segments | `backend/app/services/subtitle.py` |
| Glossary service | Domain-specific terminology JSON loading for translation | `backend/app/services/glossary.py` |
| Overlay service | FFmpeg subtitle burn-in (defined but not invoked in pipeline) | `backend/app/services/overlay.py` |
| Job model | SQLModel ORM table for job state persistence | `backend/app/models/job.py` |
| Database module | SQLite engine + session factory | `backend/app/models/database.py` |
| Config module | Pydantic settings + STT_MODELS, TRANSLATION_ENGINES, DOMAINS registries | `backend/app/config.py` |
| STT GPU worker | RunPod Serverless faster-whisper handler (CUDA, float16) | `backend/workers/stt_worker/handler.py` |
| Frontend page | Single-page React state machine wiring all UI components | `frontend/app/page.tsx` |
| API client | fetch-based wrappers for submitJob, getJob, getModels, getDomains | `frontend/lib/api.ts` |
| Socket client | Singleton socket.io-client connection factory | `frontend/lib/socket.ts` |

## Pattern Overview

**Overall:** Three-tier cascaded ML pipeline with protocol-based swappable backends

**Key Characteristics:**
- Protocol (structural typing) used for both `TranscriptionEngine` and `TranslationEngine` — backends are swapped via factory functions, not inheritance
- Pipeline runs as a FastAPI `BackgroundTask` (single async event loop, blocking steps offloaded via `run_in_executor`)
- Real-time progress pushed over Socket.IO rooms keyed by `job:{job_id}`
- All outputs written to `{storage_path}/{job_id}/` and served as static files via `/files/` mount
- Mock mode (`settings.mock_mode = True`) short-circuits both STT and translation for local dev

## Layers

**HTTP / WebSocket Layer:**
- Purpose: Accept requests, route to handlers, push real-time events
- Location: `backend/app/main.py`, `backend/app/socket.py`, `backend/app/routers/`
- Contains: FastAPI routers, Socket.IO server, ASGI composition
- Depends on: Pipeline, models, config
- Used by: Frontend

**Pipeline Orchestration Layer:**
- Purpose: Sequence the four processing steps, update job status, emit Socket.IO events
- Location: `backend/app/pipeline.py`
- Contains: `run_job()` coroutine — the single entry point for all job processing
- Depends on: All services, job model, socket module
- Used by: `backend/app/routers/jobs.py` (via `BackgroundTasks.add_task`)

**Services Layer:**
- Purpose: Isolated, swappable implementations of each pipeline step
- Location: `backend/app/services/`
- Contains: `downloader.py`, `transcriber.py`, `translator.py`, `subtitle.py`, `glossary.py`, `overlay.py`
- Depends on: External binaries (ffmpeg, yt-dlp), external APIs, config
- Used by: Pipeline

**Data / Config Layer:**
- Purpose: Persistence and application-wide settings
- Location: `backend/app/models/`, `backend/app/config.py`
- Contains: SQLModel `Job` table, `Settings` Pydantic model, model/domain/language registries
- Depends on: SQLite
- Used by: Routers, pipeline, services

**GPU Worker Layer (separate deployment):**
- Purpose: Heavy inference on CUDA hardware — isolated from orchestration backend
- Location: `backend/workers/stt_worker/`
- Contains: RunPod handler, model cache, faster-whisper inference
- Depends on: RunPod SDK, faster-whisper, CUDA
- Used by: `RunPodTranscriber` in `backend/app/services/transcriber.py` via HTTP

**Frontend Layer:**
- Purpose: User interface — URL submission, model selection, job monitoring, video playback
- Location: `frontend/`
- Contains: Next.js App Router pages, React components, API/socket clients
- Depends on: Backend HTTP + Socket.IO
- Used by: End user browser

## Data Flow

### Primary Request Path (audio_only mode)

1. User submits YouTube URL + model config via `UrlInput` → `submitJob()` (`frontend/lib/api.ts:12`)
2. `POST /jobs` creates `Job` row in SQLite, enqueues `run_job(job_id)` as BackgroundTask (`backend/app/routers/jobs.py:41`)
3. Pipeline starts: `download_audio()` calls yt-dlp + FFmpeg, writes `audio.wav` (`backend/app/pipeline.py:60`)
4. `get_transcription_engine()` factory selects backend (RunPod/local/GPT-4o/mock) (`backend/app/services/transcriber.py:233`)
5. `transcriber.transcribe(audio_path, src_lang)` returns `list[TranscriptSegment]` (`backend/app/pipeline.py:76`)
6. `get_translation_engine()` factory selects backend; loads domain glossary via `load_glossary()` (`backend/app/services/translator.py:173`)
7. `translator.translate(segments)` returns translated `list[TranscriptSegment]` (`backend/app/pipeline.py:91`)
8. `generate_srt()` writes `subtitles.srt` to `{storage_path}/{job_id}/` (`backend/app/services/subtitle.py:23`)
9. `emit_done()` pushes `job:done` Socket.IO event with `srt_url` and `embed_url` (`backend/app/socket.py:15`)
10. Frontend `JobStatus` receives event, updates React state, renders download link + `VideoPlayer` with YouTube embed

### Socket.IO Progress Path

1. Frontend calls `createSocket()` (`frontend/lib/socket.ts:6`) on mount
2. `JobStatus` component subscribes to `job:{job_id}` room via `subscribe` socket event
3. Pipeline emits `job:progress` at each step (5% → 30% → 60% → 80% → 100%) (`backend/app/socket.py:7`)
4. `job:done` or `job:error` terminates the subscription

**State Management:**
- Backend: SQLite `Job` row is source of truth for job state; `GET /jobs/{id}` allows polling fallback
- Frontend: Plain `useState<JobState>` in `frontend/app/page.tsx` — no external state library

## Key Abstractions

**TranscriptSegment:**
- Purpose: Shared data transfer object between STT, translation, and subtitle generation
- Examples: `backend/app/services/transcriber.py:22`
- Pattern: `@dataclass` with `start: float`, `end: float`, `text: str`

**TranscriptionEngine Protocol:**
- Purpose: Structural interface enabling mock/local/RunPod/GPT-4o backends to be swapped without subclassing
- Examples: `backend/app/services/transcriber.py:28` — `MockTranscriber`, `LocalWhisperTranscriber`, `RunPodTranscriber`, `GPT4oTranscriber`
- Pattern: `Protocol` with single `transcribe(audio_path, src_lang) -> list[TranscriptSegment]` method

**TranslationEngine Protocol:**
- Purpose: Same pattern for translation — enables Qwen-MT/NLLB/mock swapping
- Examples: `backend/app/services/translator.py:17` — `MockTranslator`, `QwenMTEngine`, `NLLBEngine`
- Pattern: `Protocol` with single `translate(segments) -> list[TranscriptSegment]` method

**Domain Glossary:**
- Purpose: Per-domain JSON files of source→target term mappings injected into translation API calls
- Examples: `backend/app/glossary/domains/` — loaded by `load_glossary(domain)` in `backend/app/services/glossary.py`
- Pattern: `dict[str, str]` — keys are source-language terms, values are target-language terms

## Entry Points

**Backend ASGI app:**
- Location: `backend/app/main.py` — `socket_app = socketio.ASGIApp(sio, other_asgi_app=app)`
- Triggers: `uvicorn backend.app.main:socket_app`
- Responsibilities: Mounts Socket.IO over FastAPI, serves `/files/` static directory, creates DB on startup

**Job creation:**
- Location: `backend/app/routers/jobs.py:41` — `POST /jobs`
- Triggers: Frontend form submission
- Responsibilities: Validates payload, persists `Job` to SQLite, enqueues `run_job` BackgroundTask

**Pipeline:**
- Location: `backend/app/pipeline.py:20` — `async def run_job(job_id: str)`
- Triggers: `BackgroundTasks.add_task(run_job, job_id)` in jobs router
- Responsibilities: Full sequential pipeline execution with status updates and error handling

**GPU STT Worker:**
- Location: `backend/workers/stt_worker/handler.py:26` — `def handler(event)`
- Triggers: RunPod Serverless invocation (HTTP from `RunPodTranscriber`)
- Responsibilities: Decode base64 audio, run faster-whisper on CUDA, return segments

**Frontend page:**
- Location: `frontend/app/page.tsx`
- Triggers: Browser navigation to `/`
- Responsibilities: Render full UI, manage `JobState` and `ModelConfig` React state

## Architectural Constraints

- **Threading:** FastAPI runs on a single async event loop. CPU-bound operations (whisper inference, FFmpeg) are offloaded via `loop.run_in_executor(None, ...)` in `backend/app/pipeline.py`. The executor uses the default `ThreadPoolExecutor`.
- **Global state:** `socket` singleton in `frontend/lib/socket.ts:3`. Model cache dict `_model_cache` in `backend/workers/stt_worker/handler.py:16`. `engine` SQLAlchemy engine in `backend/app/models/database.py:4`. `settings` singleton in `backend/app/config.py:41`.
- **Circular imports:** None detected. `transcriber.py` defines `TranscriptSegment` which `translator.py` imports — this creates a service-to-service dependency that should be monitored if either grows.
- **No job queue:** Jobs run directly as FastAPI BackgroundTasks with no Redis queue. Concurrent jobs share the same thread pool executor. Under load, long-running RunPod polls will block threads.
- **SQLite path:** Hard-coded to `sqlite:///./atat.db` in `backend/app/models/database.py:3` — path is relative to the process working directory, not `settings.storage_path`.

## Anti-Patterns

### SQLite path is not configurable

**What happens:** `DATABASE_URL = "sqlite:///./atat.db"` is hard-coded in `backend/app/models/database.py:3` — it ignores `settings` entirely.
**Why it's wrong:** The DB file lands wherever uvicorn is launched from, making it unpredictable in Docker and inconsistent with the `storage_path` setting.
**Do this instead:** Read from settings: `DATABASE_URL = f"sqlite:///{settings.storage_path}/atat.db"` or add a `database_url` field to `Settings`.

### LoRA fine-tuned model falls back to base weights silently

**What happens:** `"whisper-large-v3-lol"` maps to `"large-v3"` in both `backend/app/services/transcriber.py:57` and `backend/workers/stt_worker/handler.py:13` with a `# TODO: load LoRA from HF` comment.
**Why it's wrong:** Users selecting the LoL-tuned model receive base model results with no warning.
**Do this instead:** Either implement LoRA adapter loading from `settings.hf_stt_model_repo` or raise a `ValueError` and surface it in the job error field.

### Service-to-service import for TranscriptSegment

**What happens:** `backend/app/services/translator.py` imports `TranscriptSegment` from `backend/app/services/transcriber.py`.
**Why it's wrong:** Creates a dependency between two peer services; if `transcriber.py` is refactored, `translator.py` breaks unexpectedly.
**Do this instead:** Move `TranscriptSegment` to a shared types module, e.g., `backend/app/models/types.py`.

## Error Handling

**Strategy:** Exceptions propagate up to `run_job()` in `backend/app/pipeline.py` which catches all exceptions, calls `_update(JobStatus.error, 0, error=str(exc))` to persist the error, emits `job:error` over Socket.IO, and re-raises.

**Patterns:**
- HTTP API errors from external services (RunPod, Qwen-MT, OpenAI) raise `RuntimeError` with the response body included
- FFmpeg subprocess failures check `returncode != 0` and raise `RuntimeError` with stderr
- Missing configuration (API keys, worker URLs) raises `ValueError` at engine instantiation time, which becomes a job error

## Cross-Cutting Concerns

**Logging:** Python `logging` module. Configured in `backend/app/main.py:5` with `%(asctime)s %(levelname)s %(name)s — %(message)s`. Each module gets `logger = logging.getLogger(__name__)`. All pipeline steps log with `[job_id]` prefix for correlation.
**Validation:** Pydantic `BaseModel` for HTTP request/response schemas in routers. `pydantic_settings.BaseSettings` for environment config.
**Authentication:** None — personal tool, no auth layer present.

---

*Architecture analysis: 2026-06-17*
