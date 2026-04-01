# LoL Esports Video Transcriber & Translator

## Project overview

A personal web application that transcribes and translates YouTube videos (VODs and livestreams) from Korean to English, with a focus on League of Legends esports content (LCK broadcasts). The system uses fine-tuned open-source STT and translation models optimized for LoL domain terminology (champion names, abilities, items, player IGNs, team names, Korean gaming slang).

## Architecture

Three services, cloud-based (no local GPU):

### 1. Frontend (Next.js)
- **Stack**: Next.js 14+ (App Router), React, Tailwind CSS
- **Video player**: hls.js for HLS playback (livestreams), native `<video>` for VODs
- **Real-time comms**: socket.io WebSocket for receiving subtitle events as they're generated
- **Model selector**: Dropdown letting user pick STT model (Whisper variants + LoRA checkpoints) and translation engine (Qwen-MT / NLLB / LLM)
- **State management**: Zustand or plain React useState (personal tool, keep simple)
- **Deployment**: Vercel free tier or localhost

### 2. Processing backend (FastAPI + serverless GPU)
Split into two tiers:

**CPU orchestration layer** (always-on, cheap VPS ~$6/mo on Hetzner/DigitalOcean):
- FastAPI web server with WebSocket endpoint
- yt-dlp (Python library) + FFmpeg for video/audio fetching
- Redis for job queue
- SQLite via SQLModel for job history, user preferences, glossary storage
- FFmpeg for subtitle overlay (burn SRT/ASS into video) and format conversion
- Local filesystem for temp files (processed videos, audio, subtitles)

**GPU inference workers** (serverless, scale-to-zero, RunPod Serverless or Modal):
- **STT worker**: faster-whisper with LoRA checkpoint loading. Receives audio chunks, returns Korean text + timestamps
- **Translation worker**: Swappable backend (Qwen-MT API for best quality, or self-hosted NLLB-200 for offline). Returns English text with preserved timestamps

Data flow: User pastes URL → FastAPI enqueues job → yt-dlp downloads audio → sends to GPU STT worker → Korean text → translation engine → English text → generate SRT → either burn subtitles with FFmpeg (VOD) or push via WebSocket (livestream)

### 3. Training service (on-demand cloud GPU)
Not a web server — a collection of Python scripts/notebooks run on Colab Pro ($10/mo), Vast.ai, or RunPod when new training data is available.

- **Whisper LoRA fine-tuning**: HuggingFace Transformers + PEFT library. Base model: openai/whisper-large-v3. LoRA config: r=32, lora_alpha=64, target_modules=[q_proj, v_proj, k_proj, out_proj, fc1, fc2], dropout=0.05. Trains on T4 (16GB) in ~6-8 hours. Checkpoints are ~60MB.
- **NLLB-200 fine-tuning**: HuggingFace Trainer with NLLB-200-Distilled-600M or 3.3B. For Korean→English domain translation pairs.
- **Data pipeline**: Scripts for downloading LCK VOD audio, extracting YT auto-captions, generating synthetic training data via TTS, and manual correction tooling.
- **Model registry**: Push LoRA adapters and NLLB checkpoints to HuggingFace Hub. Inference workers pull latest checkpoint on startup.

## Key technical decisions

### STT: Whisper large-v3 with LoRA fine-tuning
- Use `faster-whisper` (CTranslate2) for inference — 4x faster than base Whisper, lower memory
- LoRA fine-tuning lets us train on <8GB VRAM, checkpoints are ~60MB (vs 7GB for full fine-tune)
- Fine-tune on Korean LCK esports audio to improve recognition of: champion names (오리아나→Orianna), player names (페이커→Faker), ability names (쇼크웨이브→Shockwave), items, team abbreviations, gaming jargon
- Training data strategy: real LCK VOD audio with corrected transcripts + synthetic TTS data with LoL glossary sentences
- Whisper's `--task translate` (Korean→English) only works with medium/large models, NOT turbo

### Translation: Multi-backend with glossary
- **Primary**: Qwen-MT Turbo API — best Korean quality, $0.50/M output tokens, has built-in terminology intervention (pass LoL glossary as `terms` parameter in API)
- **Secondary**: NLLB-200-Distilled-600M or 3.3B fine-tuned on LoL domain parallel data — for offline/self-hosted use
- **Tertiary**: General LLM (GPT-4o, Claude, Qwen3-8B) with prompt engineering + glossary — highest quality but most expensive
- Implement a `TranslationEngine` protocol so backends are swappable

### Why not end-to-end models?
- Meta SeamlessM4T/SeamlessStreaming could do Korean→English in one model, but: CC BY-NC 4.0 license (non-commercial), needs 40GB+ VRAM for large model, less fine-tuning community support
- Cascaded approach (Whisper STT → separate translation) gives more control over each stage and easier debugging

## Domain: LoL esports terminology

The core challenge. General ASR models butcher esports vocabulary. Key term categories to handle:

- **Champions** (160+): 오리아나→Orianna, 아지르→Azir, 제드→Zed, 르블랑→LeBlanc
- **Abilities**: 쇼크웨이브→Shockwave, 황제의 분할→Emperor's Divide, 텔레포트→Teleport
- **Items** (200+): 무한의 대검→Infinity Edge, 징후의 검→Blade of the Ruined King
- **Player IGNs**: 페이커→Faker, 구마유시→Gumayusi, 제우스→Zeus
- **Teams**: T1, 젠지→Gen.G, 한화생명→Hanwha Life, DRX, KT
- **Game terms**: 갱킹→ganking, 드래곤 소울→Dragon Soul, 바론→Baron, 미니언→minion, 포탑→turret
- **Caster expressions**: Korean caster speech patterns, hype phrases, rapid-fire commentary

Build and maintain a comprehensive glossary file (JSON) that feeds into both the STT prompt and the translation term intervention.

## Cloud GPU strategy

No local GPU. All GPU work is cloud-based:

| Workload | Platform | GPU | Cost |
|----------|----------|-----|------|
| Training (iterating) | Google Colab Pro | T4 / A100 | $10/mo subscription |
| Training (long runs) | Vast.ai / RunPod | A100 80GB | ~$0.80-1.20/hr |
| Inference (STT) | RunPod Serverless / Modal | T4 or L4 | Pay-per-second, scale to zero |
| Inference (translation) | Qwen-MT API | N/A (API) | $0.50/M output tokens |

Estimated total cost: $15-25/month for personal use.

## Project structure (planned)

```
atat/
├── CLAUDE.md                          # This file
├── docs/
│   ├── architecture.md                # Detailed architecture + diagrams
│   ├── models.md                      # STT & translation model comparison
│   ├── training-guide.md              # How to fine-tune models
│   └── glossary-format.md             # LoL terminology glossary spec
├── frontend/                          # Next.js app
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx                   # Main page with URL input + video player
│   │   └── api/                       # API routes proxying to backend
│   ├── components/
│   │   ├── VideoPlayer.tsx            # hls.js player with subtitle overlay
│   │   ├── UrlInput.tsx               # YouTube URL input + submit
│   │   ├── ModelSelector.tsx          # STT + translation model picker
│   │   ├── SubtitleOverlay.tsx        # Real-time subtitle rendering
│   │   └── JobStatus.tsx              # Processing progress indicator
│   └── lib/
│       ├── socket.ts                  # WebSocket client
│       └── api.ts                     # Backend API client
├── backend/                           # FastAPI app
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                    # FastAPI app + WebSocket endpoint
│   │   ├── config.py                  # Settings, model registry, API keys
│   │   ├── models/                    # SQLModel database models
│   │   ├── routers/
│   │   │   ├── jobs.py                # POST /jobs, GET /jobs/{id}
│   │   │   └── models.py             # GET /models (available STT + translation)
│   │   ├── services/
│   │   │   ├── downloader.py          # yt-dlp + FFmpeg audio extraction
│   │   │   ├── transcriber.py         # STT engine abstraction
│   │   │   ├── translator.py          # Translation engine abstraction (Protocol)
│   │   │   ├── subtitle.py            # SRT/ASS generation from timestamped text
│   │   │   └── overlay.py             # FFmpeg subtitle burn-in
│   │   ├── workers/
│   │   │   ├── stt_worker.py          # GPU worker: faster-whisper inference
│   │   │   └── translation_worker.py  # GPU worker: NLLB / Qwen-MT
│   │   └── glossary/
│   │       └── lol_terms.json         # LoL terminology glossary
│   ├── Dockerfile
│   └── docker-compose.yml             # Backend + Redis
├── training/                          # Training scripts + notebooks
│   ├── notebooks/
│   │   ├── whisper_lora_finetune.ipynb
│   │   └── nllb_finetune.ipynb
│   ├── scripts/
│   │   ├── download_vods.py           # yt-dlp batch VOD download
│   │   ├── extract_captions.py        # Pull YT auto-generated subs
│   │   ├── generate_synthetic.py      # TTS synthesis of glossary sentences
│   │   ├── prepare_dataset.py         # Package into HF Dataset format
│   │   └── evaluate.py                # WER evaluation on test set
│   ├── data/
│   │   ├── glossary/
│   │   │   └── lol_ko_en.json         # Master KO→EN glossary
│   │   └── README.md                  # Data sourcing notes
│   └── configs/
│       ├── whisper_lora.yaml          # LoRA hyperparameters
│       └── nllb_finetune.yaml         # NLLB training config
└── README.md
```

## Implementation priorities

### Phase 1: Basic pipeline (get it working end-to-end)
1. Backend: FastAPI + yt-dlp + FFmpeg audio extraction
2. Backend: Integrate faster-whisper (base model, no fine-tuning) for Korean STT
3. Backend: Integrate Qwen-MT API for Korean→English translation
4. Backend: SRT generation + FFmpeg subtitle burn-in
5. Frontend: URL input form, job submission, download result
6. Deploy: Backend on cheap VPS, inference via RunPod Serverless

### Phase 2: Real-time + polish
1. WebSocket subtitle streaming for near-real-time display
2. Frontend video player with subtitle overlay
3. Model selector UI
4. Livestream support (HLS audio chunking pipeline)
5. Job history and re-processing

### Phase 3: Domain fine-tuning
1. Build LoL glossary (JSON)
2. Collect LCK VOD training data (audio + corrected transcripts)
3. Generate synthetic training data via TTS
4. Fine-tune Whisper large-v3 with LoRA on Colab Pro
5. Fine-tune NLLB-200 on LoL domain parallel data
6. Evaluate WER improvement on LoL-specific test set
7. Deploy fine-tuned checkpoints to inference workers

### Phase 4: Advanced features
1. Self-hosted translation model (Qwen3-8B or fine-tuned NLLB) for API-free operation
2. Batch processing (queue multiple VODs)
3. Translation memory / caching for repeated terms
4. Export subtitles in multiple formats (SRT, ASS, VTT)

## Key dependencies

### Backend (Python)
- fastapi, uvicorn, python-socketio
- yt-dlp
- faster-whisper
- transformers, peft (for loading LoRA checkpoints)
- redis, celery (or arq for lighter alternative)
- sqlmodel
- ffmpeg-python (or subprocess calls to ffmpeg binary)
- httpx (for Qwen-MT API calls)

### Frontend (Node.js)
- next, react, react-dom
- tailwindcss
- hls.js
- socket.io-client
- zustand (state management)

### Training
- transformers, peft, bitsandbytes, accelerate
- datasets, evaluate, jiwer
- yt-dlp (data collection)
- TTS library (for synthetic data: kokoro-tts or coqui-tts)
- wandb (experiment tracking)

### Infrastructure
- Docker, docker-compose
- FFmpeg binary (not the Python package)
- Redis

## Important notes

- yt-dlp requires ffmpeg binary (not the Python ffmpeg package) and yt-dlp-ejs + a JS runtime for full YouTube support
- Whisper turbo model does NOT support translation task — use medium or large for Korean→English
- faster-whisper is the CTranslate2-optimized version — much faster inference than base openai-whisper
- Qwen-MT API has a `terms` parameter for glossary injection — use this for LoL terminology
- NLLB-200 language codes: Korean = kor_Hang, English = eng_Latn
- LoRA checkpoints from PEFT can be loaded on top of base Whisper in faster-whisper using the HuggingFace transformers pipeline
- For livestreams, yt-dlp supports HLS with `--hls-use-mpegts` flag
- Whisper encoder handles max 30-second audio segments — chunk longer audio accordingly
