# Architecture

## System overview

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Vercel / localhost)                       │
│  Next.js 14 + React + Tailwind + hls.js             │
│  URL input │ Video player │ Model selector │ WS      │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS + WebSocket
┌──────────────────────▼──────────────────────────────┐
│  Orchestration backend (CPU VPS ~$6/mo)             │
│  FastAPI + Redis + SQLite                           │
│  yt-dlp │ FFmpeg │ Job queue │ Subtitle generation  │
└──────────┬──────────────────────────┬───────────────┘
           │ API call                 │ API call
┌──────────▼──────────┐  ┌───────────▼───────────────┐
│  STT worker (GPU)   │  │  Translation worker       │
│  RunPod / Modal     │  │  Qwen-MT API or GPU NLLB  │
│  faster-whisper     │  │  Scales to zero            │
│  Scales to zero     │  │                            │
└──────────┬──────────┘  └───────────┬───────────────┘
           │                         │
           └─────────┬───────────────┘
                     │ Checkpoints from HuggingFace Hub
┌────────────────────▼────────────────────────────────┐
│  Training (on-demand cloud GPU)                      │
│  Colab Pro / Vast.ai / RunPod                        │
│  Whisper LoRA │ NLLB fine-tune │ Data pipeline       │
└──────────────────────────────────────────────────────┘
```

## Service details

### Frontend

**Deployment**: Vercel free tier (automatic from GitHub push) or `npm run dev` locally.

**Pages**:
- `/` — Main page. URL input at top, video player below, subtitle display area, model selection sidebar/drawer.
- `/history` — Past jobs with links to re-download or re-process.

**Real-time flow**:
1. User pastes YouTube URL, selects STT model + translation engine, clicks "Process"
2. Frontend POSTs to `/api/jobs` (Next.js API route proxying to backend)
3. Backend returns `{ job_id: "..." }`
4. Frontend opens WebSocket to backend `ws://backend:8000/ws/{job_id}`
5. Backend pushes status events: `downloading`, `transcribing`, `translating`, `rendering`
6. For livestreams: backend pushes subtitle events `{ start: 12.5, end: 15.2, text: "Faker lands the Shockwave!" }`
7. Frontend renders subtitles in overlay div synced to video currentTime
8. For VODs: backend pushes `{ status: "complete", download_url: "/files/abc123.mp4" }`

### Backend

**Deployment**: Docker container on Hetzner CX22 ($5.39/mo, 2 vCPU, 4GB RAM) or DigitalOcean Basic Droplet ($6/mo). Redis runs as a separate container or sidecar.

**docker-compose.yml structure**:
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379
      - QWEN_MT_API_KEY=${QWEN_MT_API_KEY}
      - RUNPOD_API_KEY=${RUNPOD_API_KEY}
      - HF_TOKEN=${HF_TOKEN}
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

**API endpoints**:
- `POST /jobs` — Submit a new transcription/translation job
  - Body: `{ url: string, stt_model: string, translation_engine: string, source_lang: "ko", target_lang: "en" }`
  - Returns: `{ job_id: string }`
- `GET /jobs/{job_id}` — Poll job status
- `GET /jobs/{job_id}/subtitles` — Download SRT file
- `GET /jobs/{job_id}/video` — Download processed video
- `WS /ws/{job_id}` — WebSocket for real-time status + subtitle events
- `GET /models` — List available STT models and translation engines

**Job processing flow** (in Celery/arq worker on the VPS):
```
1. Download audio: yt-dlp -f bestaudio -x --audio-format wav <url>
2. Chunk audio into ≤30s segments (Whisper limit)
3. Send chunks to STT GPU worker → Korean text + timestamps
4. Send Korean text to translation engine → English text
5. Generate SRT/ASS subtitle file
6. For VOD: burn subtitles with FFmpeg → MP4
7. For livestream: push subtitle events via WebSocket
```

### GPU inference workers

**Option A: RunPod Serverless**
- Deploy a Docker container with faster-whisper + model weights
- RunPod scales to zero when no requests (no idle cost)
- Cold start ~10-30 seconds (acceptable since user waits for download anyway)
- STT worker: receives audio file URL or base64, returns JSON with segments
- Cost: ~$0.00015/sec on community T4

**Option B: Modal**
- Python-native, no Docker needed
- Define functions with `@app.function(gpu="T4")` decorator
- Sub-5-second cold starts
- $30/mo free credits (may cover light personal use entirely)
- Tighter integration if using Modal for both inference and training

**Translation worker options**:
- **Qwen-MT API** (recommended): No GPU needed, call via httpx. ~$0.50/M output tokens. Pass LoL glossary in `terms` parameter.
- **Self-hosted NLLB**: Deploy NLLB-200-600M on same serverless GPU worker. Runs on T4, ~2GB VRAM. Fast inference (~50ms/sentence).
- **LLM API**: Call GPT-4o-mini or Claude via their APIs with prompt + glossary. Higher quality, higher cost.

### Training service

Not deployed as a service. A collection of scripts and notebooks run manually.

**Recommended workflow**:
1. Collect data on laptop (yt-dlp downloads, subtitle extraction)
2. Prepare and clean data on laptop (manual correction, alignment)
3. Upload dataset to HuggingFace Hub (private dataset)
4. Open Colab Pro notebook, connect to T4/A100
5. Run training notebook (pulls dataset from HF Hub)
6. Push trained LoRA adapter to HF Hub (private model)
7. Inference workers automatically pick up new checkpoint on next cold start

## Network flow

```
User → Vercel (frontend) → Hetzner VPS (FastAPI)
                                ├→ YouTube (yt-dlp download)
                                ├→ RunPod (STT GPU worker)
                                ├→ Qwen-MT API (translation)
                                └→ User (WebSocket subtitles / file download)
```

## Security considerations (personal tool)

- API keys (Qwen-MT, RunPod, HF) stored as environment variables, never in code
- No user authentication needed (personal tool, single user)
- If exposed to internet: add a simple bearer token or basic auth
- yt-dlp may need YouTube cookies for age-restricted content: use `--cookies-from-browser` flag
- SQLite DB stores job history only, no sensitive data

## Cost breakdown

| Component | Monthly cost |
|-----------|-------------|
| VPS (Hetzner CX22) | $5.39 |
| Vercel (free tier) | $0 |
| Colab Pro (training) | $10 |
| RunPod serverless (~10 hrs GPU/mo) | ~$3-5 |
| Qwen-MT API (~100K tokens/mo) | ~$0.05 |
| HuggingFace Hub (free private repos) | $0 |
| **Total** | **~$18-25/mo** |
