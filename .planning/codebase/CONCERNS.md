# Codebase Concerns

**Analysis Date:** 2026-06-17

## Tech Debt

**LoRA fine-tuned model not actually loaded:**
- Issue: `whisper-large-v3-lol` is advertised as a LoL-fine-tuned model in the UI and config but both the orchestration worker (`backend/app/workers/stt_worker.py`) and the RunPod handler (`backend/workers/stt_worker/handler.py`) silently fall back to the base `large-v3` weights. The LoRA adapter is never loaded.
- Files: `backend/app/services/transcriber.py:61`, `backend/workers/stt_worker/handler.py:13`
- Impact: Users selecting the "LoL fine-tuned" model receive identical output to the base model with no error or warning; the core domain-specialization feature is non-functional.
- Fix approach: Implement `HF_STT_MODEL_REPO` loading in the worker using `peft` + `faster-whisper`'s CTranslate2 converter, or remove the option from the UI until the adapter is ready.

**`updated_at` field never updated:**
- Issue: `Job.updated_at` in `backend/app/models/job.py:34` uses `default_factory=datetime.utcnow` but is never set during status transitions in `pipeline.py`. Every `_update()` call sets `status`, `progress`, and arbitrary kwargs but never touches `updated_at`.
- Files: `backend/app/models/job.py:34`, `backend/app/pipeline.py:24–34`
- Impact: The `updated_at` column always reflects creation time, making it useless for sorting or detecting stale jobs.
- Fix approach: Add `job.updated_at = datetime.utcnow()` inside the `_update()` helper in `pipeline.py`.

**`datetime.utcnow()` deprecated in Python 3.12+:**
- Issue: `backend/app/models/job.py` uses `datetime.utcnow()` which is deprecated since Python 3.12 and will raise a `DeprecationWarning` at runtime.
- Files: `backend/app/models/job.py:33–34`
- Impact: Will emit warnings in logs; will break in a future Python release.
- Fix approach: Replace with `datetime.now(timezone.utc)` and add `from datetime import timezone`.

**`@app.on_event("startup")` deprecated:**
- Issue: `backend/app/main.py:43` uses the deprecated `@app.on_event("startup")` decorator which was removed in FastAPI 0.109+.
- Files: `backend/app/main.py:43–45`
- Impact: Will raise a deprecation warning or runtime error on newer FastAPI/Starlette versions.
- Fix approach: Replace with `@asynccontextmanager` lifespan pattern.

**Duplicate STT worker implementations:**
- Issue: Two separate but nearly identical STT worker files exist: `backend/app/workers/stt_worker.py` (a legacy stub using the old RunPod `job` dict schema) and `backend/workers/stt_worker/handler.py` (the actual deployed handler using the `event` dict schema). They have diverged: the deployed handler has a model cache dict while the stub uses a global singleton, and the stub lacks VAD parameters.
- Files: `backend/app/workers/stt_worker.py`, `backend/workers/stt_worker/handler.py`
- Impact: Confusing maintenance surface; unclear which is deployed. Changes made to one won't propagate to the other.
- Fix approach: Delete `backend/app/workers/stt_worker.py` (the stub) and keep only `backend/workers/stt_worker/handler.py` as the canonical worker.

**NLLB engine ignores domain and glossary:**
- Issue: `NLLBEngine.__init__` in `backend/app/services/translator.py:148` accepts a `domain` parameter but immediately discards it — no glossary is loaded for NLLB translations. The `QwenMTEngine` does load glossaries via `load_glossary(domain)`.
- Files: `backend/app/services/translator.py:148–166`
- Impact: Domain-specific terminology (LoL champion names, etc.) is never injected into NLLB translations even when the user selects a domain, causing poor terminology accuracy.
- Fix approach: Load glossary in `NLLBEngine.__init__` and prepend a term hint to each text before tokenization, or add a post-processing glossary substitution step.

**`nllb-600m` and `nllb-3.3b` engines are identical:**
- Issue: Both `"nllb-600m"` and `"nllb-3.3b"` keys in the factory in `backend/app/services/translator.py:182–186` resolve to the same `NLLBEngine` class, which hardcodes `MODEL_ID = "facebook/nllb-200-distilled-600M"` in the worker. There is no way to select the 3.3B model.
- Files: `backend/app/services/translator.py:182–186`, `backend/app/workers/translation_worker.py:11`
- Impact: Users selecting the 3.3B translation engine receive 600M quality with no error.
- Fix approach: Pass `model_id` from engine selection through to the worker request payload, and handle model selection in the worker.

## Known Bugs

**Socket.IO CORS is fully open (`"*"`) while FastAPI CORS is restricted:**
- Symptoms: The `socketio.AsyncServer` in `backend/app/socket.py:4` uses `cors_allowed_origins="*"` while FastAPI restricts origins to `settings.cors_origins`. This inconsistency means WebSocket connections are unrestricted regardless of environment.
- Files: `backend/app/socket.py:4`, `backend/app/main.py:24–28`
- Trigger: Any origin can establish a WebSocket connection to subscribe to job events.
- Workaround: None; accept the risk for local personal use or fix for any deployed environment.

**Job status in frontend never transitions through intermediate states:**
- Symptoms: `JobStatus.tsx` listens for `job:progress` events containing a `status` string, but the backend emits statuses like `"downloading"`, `"transcribing"`, `"translating"`, `"rendering"` which are not in `STATUS_LABELS` in `JobStatus.tsx:13–18`. The label falls back to the raw status string.
- Files: `frontend/components/JobStatus.tsx:13–18`, `backend/app/pipeline.py:53–96`
- Trigger: Every job in progress.
- Workaround: Currently shows the raw status string; visually acceptable but unpolished.

**`download_hls_audio` returns a hardcoded path that may not exist:**
- Symptoms: `backend/app/services/downloader.py:80` returns `output_dir / "stream.ts"` unconditionally, but yt-dlp may save the file with a different extension depending on stream format.
- Files: `backend/app/services/downloader.py:65–80`
- Trigger: HLS livestream download where yt-dlp picks a non-`.ts` container.
- Workaround: Not called from the main pipeline currently (HLS not implemented end-to-end).

**`_poll` in `RunPodTranscriber` uses blocking `time.sleep` inside an executor:**
- Symptoms: `RunPodTranscriber._poll` calls `time.sleep(interval)` synchronously within a method that is dispatched via `loop.run_in_executor` in `pipeline.py:76`. This blocks a thread pool thread for the full polling duration (up to 600s), potentially starving the executor under concurrent jobs.
- Files: `backend/app/services/transcriber.py:206–226`, `backend/app/pipeline.py:76`
- Trigger: Any job using a RunPod STT model.
- Workaround: For single-user personal use this is acceptable; becomes a problem under any concurrency.

## Security Considerations

**No URL validation on job submission:**
- Risk: The `url` field in `JobCreate` (`backend/app/routers/jobs.py:20`) is a plain `str` with no validation. Any string is accepted and passed directly to `yt-dlp`, which could be exploited to access local files (`file://`) or internal network resources via URL schemes yt-dlp supports.
- Files: `backend/app/routers/jobs.py:19–26`, `backend/app/services/downloader.py:23`
- Current mitigation: None.
- Recommendations: Add a Pydantic `HttpUrl` validator or explicit YouTube URL pattern check. Restrict accepted URL schemes to `https://` only.

**No input validation on `stt_model`, `translation_engine`, `domain` fields:**
- Risk: These string fields in `JobCreate` are passed directly to factory functions that index into config dicts. An invalid model ID falls back to a default silently (`get_transcription_engine` falls back to `LocalWhisperTranscriber`), but there is no explicit allowlist check.
- Files: `backend/app/routers/jobs.py:21–26`, `backend/app/services/transcriber.py:233–242`
- Current mitigation: Silently uses defaults.
- Recommendations: Add `Literal` type annotations or explicit validation against `STT_MODELS` and `TRANSLATION_ENGINES` keys.

**No authentication on any endpoint:**
- Risk: All API endpoints (`/jobs`, `/models`, `/domains`) and the WebSocket are publicly accessible with no authentication layer.
- Files: `backend/app/main.py`, `backend/app/routers/jobs.py`
- Current mitigation: Acceptable for localhost personal use; CORS restricts browser origins.
- Recommendations: Add a simple API key header check or IP allowlist before any external deployment.

**Static file directory serves all job outputs without access control:**
- Risk: `app.mount("/files", StaticFiles(...))` in `backend/app/main.py:37` exposes all files under `settings.storage_path` to anyone who can guess or enumerate job UUIDs.
- Files: `backend/app/main.py:37`
- Current mitigation: UUIDs are hard to guess; acceptable for personal use.
- Recommendations: Add a signed URL or auth check before external deployment.

## Performance Bottlenecks

**`LocalWhisperTranscriber` loads model on each instantiation:**
- Problem: `LocalWhisperTranscriber.__init__` calls `WhisperModel(model_size, ...)` every time a job is processed. Loading a large-v3 model takes ~30–60 seconds on CPU.
- Files: `backend/app/services/transcriber.py:65–70`
- Cause: No model caching between requests.
- Improvement path: Add a module-level model cache dict keyed by model ID (similar to the RunPod worker's `_model_cache`).

**Entire audio file base64-encoded and sent to RunPod in a single POST:**
- Problem: `RunPodTranscriber.transcribe` reads the entire WAV file and base64-encodes it for the RunPod `/run` request. A 1-hour LCK VOD audio track at 16kHz mono WAV is ~115 MB, becoming ~155 MB base64, sent as a single JSON payload.
- Files: `backend/app/services/transcriber.py:183`
- Cause: No chunking or pre-upload to object storage before sending to GPU worker.
- Improvement path: Upload audio to S3/R2 and pass a presigned URL to the worker instead of base64.

**`GPT4oTranscriber` has no chunking for long audio:**
- Problem: `GPT4oTranscriber._to_mp3` converts the full audio file and checks against the 25 MB limit, but raises an error for long videos instead of splitting. A 30-minute video will typically exceed the limit.
- Files: `backend/app/services/transcriber.py:129–141`
- Cause: No audio splitting implemented.
- Improvement path: Implement chunked splitting using `extract_audio_segment` from `overlay.py` before uploading to the API.

**SQLite with default WAL mode on `/tmp`:**
- Problem: `backend/app/models/database.py` uses SQLite at `./atat.db` (resolved relative to the CWD at startup, which is the `backend/` directory). SQLite has no connection pooling and will serialize all writes. Under multiple concurrent jobs, DB writes will queue.
- Files: `backend/app/models/database.py:3`
- Cause: SQLite chosen for simplicity.
- Improvement path: Enable WAL mode (`PRAGMA journal_mode=WAL`) or migrate to PostgreSQL for concurrent use.

## Fragile Areas

**`Qwen-MT` response parsing relies on numbered line format:**
- Files: `backend/app/services/translator.py:83–103`
- Why fragile: The batch translation prompt numbers lines (`1. text\n2. text`) and parses the response by regex matching `^\d+\.\s+(.*)`. If the model returns multi-line sentences, preambles, or reformatted numbering, the regex fails and silently pads missing lines with the original Korean source text (untranslated).
- Safe modification: The fallback to source text is logged as a warning. Any change to batch size or prompt format risks alignment errors between input segments and output translations.
- Test coverage: No tests exist for translation parsing edge cases.

**`_split_sentences` in `GPT4oTranscriber` produces uniform fake timestamps:**
- Files: `backend/app/services/transcriber.py:106–108`, `backend/app/services/transcriber.py:160–165`
- Why fragile: The GPT-4o transcription API returns a flat text string (no timestamps). Sentences are split by punctuation and evenly distributed across the audio duration. This produces subtitles that are approximately correct for short content but will be increasingly misaligned for long videos or uneven speech cadence.
- Safe modification: The approach is acceptable as a known limitation; any improvement requires using the `verbose_json` response format with `timestamp_granularities`.
- Test coverage: None.

**`pipeline.py` `_update()` uses a new DB session per call with no retry:**
- Files: `backend/app/pipeline.py:24–34`
- Why fragile: Each status update opens and closes a SQLite session. If the DB file is locked (e.g., during another concurrent write), the update silently fails (the exception would propagate up and be caught by the outer `except Exception` in `pipeline.py:123`), potentially marking the job as errored when only the status write failed.
- Safe modification: Add explicit SQLite WAL pragma or wrap `_update()` with retry logic.
- Test coverage: None.

## Scaling Limits

**Storage (`/tmp/atat`):**
- Current capacity: Default `/tmp` filesystem on the host; typically 1–10 GB depending on deployment.
- Limit: A single 2-hour LCK VOD in video mode downloads ~1–3 GB. Five concurrent jobs exhaust `/tmp` on a typical VPS.
- Scaling path: Mount a dedicated volume for `storage_path`, or delete job files after the user downloads them (no cleanup is currently implemented).

**`BackgroundTasks` runs jobs in the FastAPI event loop:**
- Current capacity: Single-server, event-loop-based concurrency.
- Limit: Multiple simultaneous `run_job` calls each call `loop.run_in_executor` for CPU-heavy work. The default `ThreadPoolExecutor` size is `min(32, os.cpu_count() + 4)`. On a 2-core VPS, 6 threads can queue, but long-running RunPod polling (up to 600s per thread) will exhaust the pool.
- Scaling path: Replace `BackgroundTasks` with Celery + Redis for proper job queuing (as described in the architecture docs but not yet implemented).

## Dependencies at Risk

**`dashscope` SDK hardcodes international API URL:**
- Risk: `translator.py:53` manually overrides `dashscope.base_http_api_url` to the international endpoint. If Alibaba changes this URL or SDK behavior, translations silently fail.
- Impact: All Qwen-MT translations break.
- Migration plan: Use `httpx` directly against the documented REST API rather than the SDK to avoid SDK drift.

**`yt-dlp` requires frequent updates:**
- Risk: YouTube regularly changes its internal API, breaking yt-dlp. The `pyproject.toml` pins yt-dlp to a specific version, meaning breakage will occur as YouTube changes without a manual update.
- Impact: All download jobs fail with extraction errors.
- Migration plan: Use `yt-dlp >= current` with dependabot or a weekly automated update CI step.

## Missing Critical Features

**No job file cleanup:**
- Problem: `pipeline.py` never deletes the downloaded audio, raw video, or generated subtitle files from `settings.storage_path`. Every processed job accumulates files permanently.
- Blocks: Long-term operation without manual intervention to free disk space.

**No job cancellation:**
- Problem: Once a `BackgroundTasks` job starts, there is no mechanism to cancel it. If yt-dlp is mid-download of a multi-gigabyte file, the user cannot stop it from the frontend.
- Blocks: Clean UX for accidental submissions or wrong URLs.

**Livestream pipeline not implemented end-to-end:**
- Problem: `download_hls_audio` exists in `backend/app/services/downloader.py` but is never called from `pipeline.py`. The `download_mode` only handles `"audio_only"` and `"video"` — there is no `"livestream"` mode. The WebSocket real-time streaming of subtitle segments described in the architecture is not implemented.
- Blocks: The core livestream use case described in CLAUDE.md Phase 1 is incomplete.

## Test Coverage Gaps

**No tests exist anywhere in the codebase:**
- What's not tested: The entire backend (pipeline, services, routers, workers) and frontend have zero automated tests.
- Files: All files under `backend/app/`, `frontend/`
- Risk: Breaking changes in translation response parsing, subtitle generation, job status transitions, or API contracts go undetected until runtime.
- Priority: High — especially for `translator.py` batch parsing logic and `transcriber.py` response handling, which have multiple edge-case fallback paths.

---

*Concerns audit: 2026-06-17*
