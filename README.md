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
