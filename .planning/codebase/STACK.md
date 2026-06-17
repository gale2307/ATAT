# Technology Stack

**Analysis Date:** 2026-06-17

## Languages

**Primary:**
- Python 3.11+ - Backend (FastAPI app, GPU workers, services)
- TypeScript 5.4 - Frontend (Next.js app, components, lib)

**Secondary:**
- JavaScript - Next.js config files (`frontend/next.config.js`, `frontend/postcss.config.js`)

## Runtime

**Environment:**
- Node.js 20.x (frontend; also installed in backend Docker image for yt-dlp JS extractors)
- Python 3.11 (backend; enforced in `backend/pyproject.toml` with `requires-python = ">=3.11"`)

**Package Manager:**
- npm (frontend) — lockfile: not confirmed present, `package.json` at `frontend/package.json`
- pip / hatchling (backend) — build backend declared in `backend/pyproject.toml`

## Frameworks

**Core:**
- Next.js 14.2 - Frontend framework (App Router) — `frontend/app/`
- React 18.3 - UI rendering — `frontend/components/`
- FastAPI 0.111+ - Backend REST + WebSocket API — `backend/app/main.py`
- Uvicorn (standard) 0.29+ - ASGI server — entry point in `backend/Dockerfile`

**Realtime:**
- python-socketio 5.11+ - WebSocket server — `backend/app/socket.py`
- socket.io-client 4.7 - WebSocket client — `frontend/lib/socket.ts`

**State Management:**
- Zustand 4.5 - Frontend global state — `frontend/` components

**Styling:**
- Tailwind CSS 3.4 - Utility-first CSS — `frontend/tailwind.config.ts`
- PostCSS 8.4 — `frontend/postcss.config.js`

**ORM / Database:**
- SQLModel 0.0.18 - SQLite ORM (wraps SQLAlchemy + Pydantic) — `backend/app/models/`

**Job Queue:**
- arq 0.25 - Async Redis-based job queue (lighter alternative to Celery) — `backend/pyproject.toml`
- redis 5.0 (Python client) — `backend/pyproject.toml`

**Testing:**
- pytest + pytest-asyncio (backend dev dependencies) — `backend/pyproject.toml`
- ESLint 8 + eslint-config-next 14.2 (frontend lint) — `frontend/package.json`

**Build/Dev:**
- hatchling - Python build backend — `backend/pyproject.toml`
- TypeScript compiler (tsc) — strict mode, `frontend/tsconfig.json`

## Key Dependencies

**Critical:**
- `faster-whisper >= 1.0.1` - CTranslate2-optimized Whisper inference (4x faster than base). Used in GPU worker at `backend/app/workers/stt_worker.py` and the RunPod handler at `backend/workers/stt_worker/handler.py`
- `yt-dlp >= 2024.4.9` - YouTube audio/video download — `backend/app/services/downloader.py`
- `dashscope >= 1.20.0` - Alibaba DashScope SDK for Qwen-MT translation API — `backend/app/services/translator.py`
- `hls.js 1.5` - HLS stream playback in browser — `frontend/` VideoPlayer component
- `transformers >= 4.40.0` + `peft >= 0.10.0` - HuggingFace model loading + LoRA adapter support — backend
- `ffmpeg-python >= 0.2.0` - Python bindings for FFmpeg subtitle burn-in — `backend/app/services/overlay.py`

**Infrastructure:**
- `httpx >= 0.27.0` - Async HTTP client for calling GPU worker endpoints — `backend/app/services/translator.py`
- `python-multipart >= 0.0.9` - FastAPI file upload support
- `pydantic-settings >= 2.2.0` - Settings from `.env` file — `backend/app/config.py`
- `runpod` - RunPod Serverless SDK (GPU worker only) — `backend/workers/stt_worker/requirements.txt`

## Configuration

**Environment:**
- Backend reads from `backend/.env` via pydantic-settings (`SettingsConfigDict(env_file=".env")`)
- `.env.example` exists at `backend/.env.example` (contents restricted)
- Key env vars (from `backend/app/config.py`):
  - `QWEN_MT_API_KEY` - DashScope / Qwen-MT API key
  - `OPENAI_API_KEY` - OpenAI API key (for GPT-4o transcription / translation)
  - `REDIS_URL` - Redis connection string (default: `redis://localhost:6379`)
  - `STORAGE_PATH` - Temp file storage (default: `/tmp/atat`)
  - `RUNPOD_API_KEY` - RunPod Serverless API key
  - `STT_WORKER_URL` - RunPod STT worker endpoint URL
  - `TRANSLATION_WORKER_URL` - RunPod translation worker endpoint URL
  - `HF_TOKEN` - HuggingFace Hub token (for pulling fine-tuned model checkpoints)
  - `HF_STT_MODEL_REPO` - HuggingFace repo for fine-tuned STT checkpoint
  - `CORS_ORIGINS` - Allowed CORS origins (default: localhost:3000, localhost:3001)
  - `MOCK_MODE` - Disables real API calls for local dev
  - `DEBUG` - FastAPI debug mode

- Frontend reads `NEXT_PUBLIC_BACKEND_URL` for backend proxy target (default: `http://localhost:8000`)

**Build:**
- `frontend/tsconfig.json` - TypeScript strict mode, path alias `@/*` → `./`
- `frontend/next.config.js` - Rewrites `/api/backend/:path*` and `/files/:path*` to backend URL
- `frontend/tailwind.config.ts` - Tailwind configuration
- `backend/pyproject.toml` - Python project metadata and dependencies
- `backend/Dockerfile` - Python 3.11-slim base, installs FFmpeg binary + Node.js 20
- `backend/docker-compose.yml` - Orchestrates `backend` + `redis:7-alpine` services

## Platform Requirements

**Development:**
- FFmpeg binary (system-level, required by yt-dlp and ffmpeg-python)
- Node.js 20 (in backend Docker image for yt-dlp YouTube JS extractors)
- Redis (via Docker or local install)
- Python 3.11+
- CUDA-capable GPU for STT inference (only on RunPod workers, not local)

**Production:**
- Backend: Docker container on cheap VPS (Hetzner/DigitalOcean ~$6/mo) behind Docker Compose
- Frontend: Vercel free tier or localhost
- GPU workers: RunPod Serverless (scale-to-zero, pay-per-second, T4/L4 GPUs)
- CI/CD: GitHub Actions (`build-stt-worker.yml`) builds and pushes STT worker Docker image to Docker Hub on changes to `backend/workers/stt_worker/**`

---

*Stack analysis: 2026-06-17*
