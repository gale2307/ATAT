# Codebase Structure

**Analysis Date:** 2026-06-17

## Directory Layout

```
ATAT/
├── backend/                        # FastAPI Python backend
│   ├── app/                        # Application package
│   │   ├── main.py                 # FastAPI + Socket.IO ASGI entry point
│   │   ├── pipeline.py             # Job orchestration (download→transcribe→translate→subtitle)
│   │   ├── config.py               # Settings (pydantic-settings) + model/domain registries
│   │   ├── socket.py               # Shared Socket.IO server instance + emit helpers
│   │   ├── models/                 # SQLModel ORM
│   │   │   ├── database.py         # SQLite engine, session factory
│   │   │   └── job.py              # Job table + JobStatus enum
│   │   ├── routers/                # FastAPI route handlers
│   │   │   ├── jobs.py             # POST /jobs, GET /jobs/{id}, GET /jobs
│   │   │   ├── models.py           # GET /models
│   │   │   └── domains.py          # GET /domains
│   │   ├── services/               # Business logic, one file per pipeline step
│   │   │   ├── downloader.py       # yt-dlp audio/video download + FFmpeg extraction
│   │   │   ├── transcriber.py      # STT Protocol + Mock/LocalWhisper/RunPod/GPT4o backends
│   │   │   ├── translator.py       # Translation Protocol + Mock/QwenMT/NLLB backends
│   │   │   ├── subtitle.py         # SRT + WebVTT file generation
│   │   │   ├── glossary.py         # Domain glossary JSON loader
│   │   │   └── overlay.py          # FFmpeg subtitle burn-in
│   │   ├── workers/                # In-process worker stubs (currently empty shell)
│   │   │   ├── stt_worker.py
│   │   │   └── translation_worker.py
│   │   └── glossary/               # Domain glossary JSON files
│   │       └── domains/            # One JSON file per domain ID
│   ├── workers/                    # Separately deployed GPU workers
│   │   └── stt_worker/             # RunPod Serverless STT worker
│   │       ├── handler.py          # RunPod handler — faster-whisper CUDA inference
│   │       ├── Dockerfile          # Container image for RunPod deployment
│   │       └── requirements.txt
│   ├── pyproject.toml              # Python dependencies + project metadata
│   ├── Dockerfile                  # Backend orchestration container
│   ├── docker-compose.yml          # Backend + Redis service composition
│   ├── .env.example                # Environment variable template
│   └── atat.db                     # SQLite database (gitignored, runtime artifact)
├── frontend/                       # Next.js 14 App Router frontend
│   ├── app/                        # App Router pages
│   │   ├── page.tsx                # Main (only) page — root "/" route
│   │   ├── layout.tsx              # Root HTML shell, global CSS import
│   │   └── globals.css             # Tailwind base styles
│   ├── components/                 # React UI components
│   │   ├── UrlInput.tsx            # YouTube URL input + submit button
│   │   ├── ModelSelector.tsx       # STT model, translation engine, domain, language dropdowns
│   │   ├── JobStatus.tsx           # Progress bar + Socket.IO event subscriber
│   │   ├── VideoPlayer.tsx         # hls.js / native video player with subtitle track
│   │   └── SubtitleOverlay.tsx     # Real-time subtitle rendering overlay
│   ├── lib/                        # Shared client utilities
│   │   ├── api.ts                  # fetch wrappers: submitJob, getJob, getModels, getDomains
│   │   └── socket.ts               # socket.io-client singleton factory
│   ├── next.config.js              # Next.js config
│   ├── tailwind.config.ts          # Tailwind config
│   ├── tsconfig.json               # TypeScript config with `@/` path alias
│   └── package.json                # Node.js dependencies
├── training/                       # Offline model fine-tuning (not deployed)
│   ├── notebooks/                  # Jupyter notebooks (Colab/Vast.ai)
│   ├── scripts/                    # Data pipeline Python scripts
│   │   ├── download_vods.py
│   │   ├── extract_captions.py
│   │   ├── generate_synthetic.py
│   │   ├── prepare_dataset.py
│   │   └── evaluate.py
│   ├── configs/                    # YAML training hyperparameters
│   │   ├── whisper_lora.yaml
│   │   └── nllb_finetune.yaml
│   └── data/                       # Training data and master glossary
│       ├── lol_ko_en.json          # Master KO→EN LoL terminology glossary
│       └── glossary/
├── docs/                           # Human-readable documentation
│   ├── architecture.md
│   ├── models.md
│   ├── training-guide.md
│   └── glossary-format.md
├── .planning/                      # GSD planning artifacts (not deployed)
│   └── codebase/                   # Codebase map documents
├── .claude/                        # Claude / GSD tooling configuration
├── CLAUDE.md                       # Project context for Claude (this repo)
└── README.md
```

## Directory Purposes

**`backend/app/`:**
- Purpose: The Python backend application package
- Contains: Entry point, pipeline, routers, services, models, config, socket helpers
- Key files: `main.py`, `pipeline.py`, `config.py`

**`backend/app/services/`:**
- Purpose: One file per pipeline step — each is independently testable and swappable
- Contains: Protocol definitions, concrete backend implementations, factory functions
- Key files: `transcriber.py`, `translator.py`, `downloader.py`

**`backend/app/glossary/domains/`:**
- Purpose: Domain-specific terminology JSON files keyed by domain ID
- Contains: `{domain-id}.json` files, each a flat `{"source_term": "target_term"}` dict
- Key files: Any file named after a domain ID from `config.py:DOMAINS` (e.g., `lol-esports.json`)

**`backend/workers/stt_worker/`:**
- Purpose: Separately containerized RunPod Serverless worker for GPU inference
- Contains: `handler.py` (RunPod entry point), `Dockerfile`, `requirements.txt`
- Note: Deployed independently to RunPod — not part of the main backend container

**`backend/app/workers/`:**
- Purpose: Placeholder — currently empty stubs (`stt_worker.py`, `translation_worker.py`)
- Note: Do not confuse with `backend/workers/` which contains real GPU worker code

**`frontend/components/`:**
- Purpose: Reusable React UI components, each a single `.tsx` file
- Contains: All visual UI elements used by `app/page.tsx`

**`frontend/lib/`:**
- Purpose: Non-component client utilities (API calls, WebSocket connection)
- Contains: `api.ts`, `socket.ts`

**`training/`:**
- Purpose: Offline-only model training pipeline — never deployed as a service
- Contains: Colab notebooks, data scripts, YAML configs, training data
- Note: Run manually on Colab/Vast.ai/RunPod; outputs pushed to HuggingFace Hub

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: ASGI app (`socket_app`) — run with `uvicorn backend.app.main:socket_app`
- `frontend/app/page.tsx`: Single-page React app root
- `backend/workers/stt_worker/handler.py`: RunPod Serverless handler function

**Configuration:**
- `backend/app/config.py`: All settings (`Settings` class) + `STT_MODELS`, `TRANSLATION_ENGINES`, `DOMAINS`, `LANGUAGE_PAIRS` registries
- `backend/.env`: Runtime secrets and overrides (not committed; see `.env.example`)
- `frontend/.env.local`: `NEXT_PUBLIC_BACKEND_URL` for backend URL
- `frontend/tsconfig.json`: TypeScript config; defines `@/` alias pointing to `frontend/`

**Core Logic:**
- `backend/app/pipeline.py`: The `run_job()` function — main processing logic
- `backend/app/services/transcriber.py`: STT Protocol + all backends + factory
- `backend/app/services/translator.py`: Translation Protocol + all backends + factory
- `backend/app/services/downloader.py`: yt-dlp and FFmpeg wrappers

**Database:**
- `backend/app/models/job.py`: `Job` SQLModel table definition
- `backend/app/models/database.py`: Engine creation and session factory
- `backend/atat.db`: SQLite file (runtime, not committed)

## Naming Conventions

**Python files:**
- `snake_case.py` for all modules
- Service files named after their pipeline step: `downloader.py`, `transcriber.py`, `translator.py`, `subtitle.py`
- One Protocol class + multiple concrete implementations per service file

**TypeScript/React files:**
- `PascalCase.tsx` for React components: `VideoPlayer.tsx`, `JobStatus.tsx`
- `camelCase.ts` for utility modules: `api.ts`, `socket.ts`
- App Router pages follow Next.js convention: `page.tsx`, `layout.tsx`

**Python classes:**
- `PascalCase` for all classes: `Job`, `JobStatus`, `TranscriptSegment`, `QwenMTEngine`
- Engine/backend classes suffixed with their role: `MockTranscriber`, `RunPodTranscriber`, `LocalWhisperTranscriber`
- Protocol classes named after the interface: `TranscriptionEngine`, `TranslationEngine`

**Glossary files:**
- `{domain-id}.json` matching the `id` field in `config.py:DOMAINS`, e.g., `lol-esports.json`, `erbs-general.json`

**Job IDs:**
- UUID4 strings generated in `backend/app/routers/jobs.py:42`
- Used as both the SQLite `job_id` column and the filesystem directory name under `storage_path`

## Where to Add New Code

**New STT backend:**
- Implement the `TranscriptionEngine` Protocol (add `transcribe(audio_path, src_lang) -> list[TranscriptSegment]` method)
- Add the class to `backend/app/services/transcriber.py`
- Register the model ID in `STT_MODELS` dict in `backend/app/config.py:43`
- Add a branch to the `get_transcription_engine()` factory at `backend/app/services/transcriber.py:233`

**New translation backend:**
- Implement the `TranslationEngine` Protocol (add `translate(segments) -> list[TranscriptSegment]` method)
- Add the class to `backend/app/services/translator.py`
- Register in `TRANSLATION_ENGINES` list in `backend/app/config.py:51`
- Add to the `engines` dict in `get_translation_engine()` at `backend/app/services/translator.py:182`

**New domain:**
- Add an entry to the `DOMAINS` list in `backend/app/config.py:58` with a unique `id`, `label`, `description`, and `system_prompt`
- Create `backend/app/glossary/domains/{domain-id}.json` as a flat `{"source": "target"}` JSON object

**New API endpoint:**
- Add a new router file to `backend/app/routers/`
- Import and mount it in `backend/app/main.py` with `app.include_router(...)`

**New React component:**
- Add `ComponentName.tsx` to `frontend/components/`
- Import using the `@/components/ComponentName` path alias

**New frontend utility:**
- Add to `frontend/lib/` as a `camelCase.ts` file

**New training script:**
- Add to `training/scripts/` as a standalone Python script

## Special Directories

**`.planning/`:**
- Purpose: GSD planning documents and codebase maps
- Generated: By GSD tooling
- Committed: Yes

**`.claude/`:**
- Purpose: Claude Code / GSD tooling configuration, commands, and hooks
- Generated: By GSD installer
- Committed: Yes

**`frontend/.next/`:**
- Purpose: Next.js build output and cache
- Generated: Yes (`npm run build` / `next dev`)
- Committed: No (gitignored)

**`backend/app/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (gitignored)

**`backend/app/workers/` (in-process stubs):**
- Purpose: Placeholder stubs — currently contain no meaningful implementation
- Note: Real GPU worker code lives in `backend/workers/stt_worker/`, not here

---

*Structure analysis: 2026-06-17*
