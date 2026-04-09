# ATAT — Auto Transcribe and Translate

A personal web application that transcribes and translates YouTube videos (VODs and livestreams) into subtitles. Supports multiple languages and media domains (esports, K-pop, K-drama, anime, tech) using fine-tuned open-source STT and translation models with domain-specific glossary injection.

## Features

- Paste a YouTube URL or livestream link, get subtitles in any supported language pair
- Domain-aware glossary injection (LoL esports, K-pop, K-drama, anime, tech, or general)
- Swappable translation backends (Qwen-MT API, NLLB-200, GPT-4o)
- Real-time subtitle streaming for livestreams via WebSocket
- Downloadable subtitled video for VODs (SRT / WebVTT)
- Model selector — pick STT model, translation engine, language pair, and domain per job

## Quick start

```bash
git clone <repo-url>
cd atat
```

### macOS

```bash
# System dependencies
brew install ffmpeg

# Backend
cd backend
cp .env.example .env  # fill in API keys
conda create -n atat python=3.11 -y && conda activate atat
pip install -e .
uvicorn app.main:socket_app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Linux (Debian / Ubuntu)

```bash
# System dependencies
sudo apt update
sudo apt install -y ffmpeg

# Backend
cd backend
cp .env.example .env  # fill in API keys
conda create -n atat python=3.11 -y && conda activate atat
pip install -e .
uvicorn app.main:socket_app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Linux (RHEL / Fedora)

```bash
# System dependencies
sudo dnf install -y ffmpeg

# Backend and frontend steps are the same as above
```

Open http://localhost:3000, paste a video URL, choose your language pair and domain, and submit.

> **Local dev tip:** Set `MOCK_MODE=true` in `backend/.env` to skip Whisper and translation API calls — the pipeline will return static dummy subtitles so you can test the full UI flow without GPU or API keys.

## RunPod STT worker

The STT worker runs `faster-whisper` on a GPU via RunPod Serverless. It only runs when a job is submitted (scale to zero) and costs ~$0.004 per 5-minute clip.

### Build and push the Docker image

The image is built and pushed automatically via GitHub Actions whenever `backend/workers/stt_worker/` changes. To set it up:

1. Add two repository secrets in **GitHub → Settings → Secrets and variables → Actions**:
   - `DOCKERHUB_USERNAME` — your Docker Hub username
   - `DOCKERHUB_TOKEN` — a Docker Hub access token with Read & Write permission (Docker Hub → Account Settings → Personal access tokens)

2. Push to `main` — the workflow in `.github/workflows/build-stt-worker.yml` triggers automatically and pushes `<your-username>/atat-stt-worker:latest` to Docker Hub in ~5 minutes.

   You can also trigger it manually from the **Actions** tab → **Build & push STT worker** → **Run workflow**.

> **Why not build locally?** The CUDA base image is several GB. Pushing it over a home connection takes longer than the Docker Hub upload session timeout (30 min), causing a `400 Bad Request` error. GitHub Actions has a fast datacenter connection and avoids this.

### Create the RunPod endpoint

1. Go to [runpod.io](https://runpod.io) → **Serverless** → **+ New Endpoint**
2. Set:
   - **Container image**: `<your-dockerhub-username>/atat-stt-worker:latest`
   - **GPU type**: RTX 3090 or A4000 (16 GB VRAM)
   - **Min workers**: 0
   - **Max workers**: 1
3. Save and copy the **Endpoint ID** from the URL

### Configure the backend

Add to `backend/.env`:

```env
RUNPOD_API_KEY=your_runpod_api_key
STT_WORKER_URL=https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync
```

When `STT_WORKER_URL` is set, any non-GPT-4o STT model selected in the UI will route to the RunPod worker automatically. The worker returns real per-segment timestamps, so subtitle timing is accurate.

> **Cold start**: The first request after the worker has been idle takes ~60–90 seconds while the model loads. Subsequent requests in the same session are fast (~10–30 s for a 5-minute clip). To eliminate cold starts, attach a RunPod **Network Volume** and set `download_root="/runpod-volume/models"` in `handler.py` so the model persists across restarts.

## Architecture

See [docs/architecture.md](docs/architecture.md) for full details.

- **Frontend**: Next.js 14 + React + Tailwind + hls.js (Vercel)
- **Backend**: FastAPI + Redis + yt-dlp + FFmpeg (cheap CPU VPS)
- **GPU inference**: RunPod Serverless / Modal (scale to zero)
- **Training**: Colab Pro / Vast.ai (on-demand)

## Supported domains

| Domain | Glossary coverage |
|--------|-------------------|
| General | No domain glossary |
| LoL Esports | Champions, items, abilities, player IGNs, teams, game terms |
| K-Pop | Idols, groups, industry terminology |
| K-Drama | Drama and variety show terms |
| Anime | Character types, attack names, genre terms |
| Tech / Dev | Programming, infrastructure, AI/ML terminology |

## Docs

- [CLAUDE.md](CLAUDE.md) — Full project context for AI-assisted development
- [docs/architecture.md](docs/architecture.md) — System architecture and deployment
- [docs/models.md](docs/models.md) — STT and translation model comparison
- [docs/training-guide.md](docs/training-guide.md) — How to fine-tune Whisper and NLLB
- [docs/glossary-format.md](docs/glossary-format.md) — Domain glossary specification

## License

Personal project.
