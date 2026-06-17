# External Integrations

**Analysis Date:** 2026-06-17

## APIs & External Services

**AI / Translation:**
- Alibaba DashScope (Qwen-MT) - Primary translation engine for Korean→English
  - SDK/Client: `dashscope` Python package (`backend/pyproject.toml`)
  - Model used: `qwen-mt-flash`
  - API base: `https://dashscope-intl.aliyuncs.com/api/v1` (set at runtime in `backend/app/services/translator.py`)
  - Auth: `QWEN_MT_API_KEY` env var → `settings.qwen_mt_api_key`
  - Feature: `terms` parameter used for domain glossary injection per batch

- OpenAI - GPT-4o transcription and premium translation (configured, not yet fully implemented)
  - Auth: `OPENAI_API_KEY` env var → `settings.openai_api_key`
  - Model registry entry: `"gpt-4o-transcribe"` and `"gpt-4o"` in `backend/app/config.py`

**Video / Audio:**
- YouTube (via yt-dlp) - Video/audio download and HLS stream access
  - Client: `yt-dlp >= 2024.4.9` Python library
  - Implementation: `backend/app/services/downloader.py`
  - Requires FFmpeg binary + Node.js 20 runtime for JS-based extractors (installed in `backend/Dockerfile`)
  - Supports HLS live streams via `--hls-use-mpegts` flag

**GPU Compute:**
- RunPod Serverless - Hosts STT (Whisper) and translation (NLLB) GPU workers at scale-to-zero endpoints
  - STT worker SDK: `runpod` Python package (`backend/workers/stt_worker/requirements.txt`)
  - Auth: `RUNPOD_API_KEY` env var
  - STT endpoint: `STT_WORKER_URL` env var (called from `backend/app/services/transcriber.py`)
  - Translation endpoint: `TRANSLATION_WORKER_URL` env var (called from `backend/app/services/translator.py`)
  - Worker handler: `backend/workers/stt_worker/handler.py` — receives base64 audio, returns JSON segments

**Model Registry:**
- HuggingFace Hub - Hosts fine-tuned Whisper LoRA checkpoints and NLLB-200 adapters
  - Auth: `HF_TOKEN` env var
  - Repo config: `HF_STT_MODEL_REPO` env var (pulled by workers at cold start)

**Container Registry:**
- Docker Hub - Stores STT worker Docker images
  - Auth: `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` GitHub Actions secrets
  - Image: `{DOCKERHUB_USERNAME}/atat-stt-worker:latest`
  - CI: `.github/workflows/build-stt-worker.yml` (triggers on push to `backend/workers/stt_worker/**`)

## Data Storage

**Databases:**
- SQLite
  - File: `backend/atat.db` (local filesystem, relative to backend working directory)
  - Client: SQLModel 0.0.18 (SQLAlchemy + Pydantic wrapper)
  - Engine setup: `backend/app/models/database.py` (`DATABASE_URL = "sqlite:///./atat.db"`)
  - Models: `backend/app/models/job.py`

**File Storage:**
- Local filesystem — temporary audio files, processed video files, generated SRT/ASS subtitles
  - Base path: `STORAGE_PATH` env var (default: `/tmp/atat`)
  - Docker volume: named volume `storage` mounted at `/tmp/atat` in `backend/docker-compose.yml`
  - Files served back to frontend via `/files/:path*` rewrite proxy in `frontend/next.config.js`

**Caching / Message Queue:**
- Redis 7 (Alpine)
  - Purpose: Job queue backing store for arq async workers
  - Connection: `REDIS_URL` env var (default: `redis://localhost:6379`; overridden to `redis://redis:6379` in Docker Compose)
  - Docker: `redis:7-alpine` image with named volume `redis_data` in `backend/docker-compose.yml`

## Authentication & Identity

**Auth Provider:**
- None — personal tool, no user authentication system implemented
- CORS whitelist in `backend/app/config.py` (`cors_origins` setting) restricts browser origins

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Python standard `logging` module used throughout backend services (`backend/app/services/translator.py`, others)
- Log levels: DEBUG for API call details, WARNING for response mismatches, ERROR for API failures

## CI/CD & Deployment

**Hosting:**
- Backend: Docker Compose on VPS (Hetzner or DigitalOcean) — `backend/docker-compose.yml`
- Frontend: Vercel free tier or localhost — no Vercel config file detected
- GPU workers: RunPod Serverless (serverless, scale-to-zero)

**CI Pipeline:**
- GitHub Actions — `.github/workflows/build-stt-worker.yml`
  - Triggers: push to `backend/workers/stt_worker/**` or manual `workflow_dispatch`
  - Steps: checkout → Docker Hub login → Docker Buildx setup → build and push `linux/amd64` image
  - Uses GitHub Actions cache for Docker layer caching

## Environment Configuration

**Required env vars (backend):**
- `QWEN_MT_API_KEY` - DashScope API key for Qwen-MT translation
- `OPENAI_API_KEY` - OpenAI API key (GPT-4o features)
- `REDIS_URL` - Redis connection string
- `STORAGE_PATH` - Filesystem path for temp/output files
- `RUNPOD_API_KEY` - RunPod Serverless auth
- `STT_WORKER_URL` - RunPod STT worker endpoint
- `TRANSLATION_WORKER_URL` - RunPod NLLB translation worker endpoint
- `HF_TOKEN` - HuggingFace Hub access token
- `HF_STT_MODEL_REPO` - HuggingFace repo for fine-tuned STT model
- `CORS_ORIGINS` - JSON list of allowed CORS origins
- `MOCK_MODE` - Set `true` to bypass all external API calls in local dev
- `DEBUG` - FastAPI debug mode toggle

**Required env vars (frontend):**
- `NEXT_PUBLIC_BACKEND_URL` - Backend base URL for Next.js proxy rewrites (default: `http://localhost:8000`)

**Secrets location:**
- Backend: `backend/.env` file (read by pydantic-settings; `.env.example` template present)
- CI/CD: GitHub Actions repository secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`)

## Webhooks & Callbacks

**Incoming:**
- None detected — no webhook receiver endpoints

**Outgoing:**
- WebSocket push to connected frontend clients via python-socketio — `backend/app/socket.py`
  - Sends real-time subtitle segments as they are generated during transcription/translation pipeline
  - Frontend connects via socket.io-client — `frontend/lib/socket.ts`

---

*Integration audit: 2026-06-17*
