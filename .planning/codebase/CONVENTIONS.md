# Coding Conventions

**Analysis Date:** 2026-06-17

## Naming Patterns

**Files:**
- Python: `snake_case.py` — `downloader.py`, `transcriber.py`, `translator.py`, `subtitle.py`
- TypeScript: `PascalCase.tsx` for components — `VideoPlayer.tsx`, `JobStatus.tsx`, `ModelSelector.tsx`
- TypeScript: `camelCase.ts` for library files — `api.ts`, `socket.ts`

**Functions (Python):**
- Public: `snake_case` — `download_audio`, `get_transcription_engine`, `load_glossary`
- Private: `_snake_case` prefix — `_translate_batch`, `_terms_for_batch`, `_call_api`, `_format_srt_time`

**Functions (TypeScript):**
- Components: `PascalCase` — `VideoPlayer`, `YouTubePlayer`, `Html5Player`
- Event handlers: `handle` prefix — `handleSubmit`
- Utilities: `camelCase` — `parseSrt`, `parseSrtTime`, `extractVideoId`, `loadYouTubeApi`

**Variables (Python):**
- Module-level constants: `UPPER_SNAKE_CASE` — `STT_MODELS`, `TRANSLATION_ENGINES`, `DOMAINS`, `NLLB_LANG_CODES`
- Private module-level: `_UPPER_SNAKE_CASE` — `_MOCK_SEGMENTS`, `_WHISPER_MODEL_MAP`, `_BATCH_SIZE`
- Locals/parameters: `snake_case`

**Variables (TypeScript):**
- Module-level constants: `UPPER_SNAKE_CASE` — `STATUS_LABELS`
- Locals/state: `camelCase` — `jobId`, `srtUrl`, `embedUrl`

**Types (TypeScript):**
- Interfaces/types: `PascalCase` — `JobState`, `ModelConfig`, `Segment`, `Props`
- React props type named `Props` locally in component files

**Classes (Python):**
- `PascalCase` — `QwenMTEngine`, `NLLBEngine`, `MockTranscriber`, `LocalWhisperTranscriber`, `RunPodTranscriber`

**Pydantic/SQLModel Models (Python):**
- `PascalCase` — `JobCreate`, `JobResponse`, `Settings`, `Job`

**API Field Naming:**
- Python backend uses `snake_case` for internal model fields (`stt_model`, `src_lang`)
- JSON API responses use `camelCase` (`jobId`, `outputUrl`, `srtUrl`, `embedUrl`)
- `JobResponse` in `backend/app/routers/jobs.py` explicitly maps snake_case fields to camelCase

## Code Style

**Formatting:**
- Python: No formatter config detected (no `.black`, `.ruff`, or `pyproject.toml` formatter section). Code follows PEP 8 manually.
- TypeScript: No Prettier config detected. ESLint via `eslint-config-next` only (runs `next lint`).

**Linting:**
- Frontend: ESLint via `next lint` — config inherited from `eslint-config-next`
- Backend: No linting tool configured

**Line length:**
- Python: Long lines common in logging calls and dict literals (no enforced limit)
- TypeScript: No enforced limit

**Section dividers:**
- Python service files use `# ---...---` comment blocks to separate implementation sections:
  ```python
  # ---------------------------------------------------------------------------
  # Mock
  # ---------------------------------------------------------------------------
  ```

## Import Organization

**Python order:**
1. Standard library (`import logging`, `from pathlib import Path`, `from typing import ...`)
2. Third-party (`import dashscope`, `import httpx`, `from fastapi import ...`)
3. Local app imports (`from app.config import ...`, `from app.services.transcriber import ...`)

**TypeScript order:**
1. React hooks (`import { useEffect, useRef, useState } from "react"`)
2. Third-party (`import Hls from "hls.js"`)
3. Local components (`import UrlInput from "@/components/UrlInput"`)
4. Local lib (`import { submitJob } from "@/lib/api"`)
5. Local types (`import type { JobState } from "@/app/page"`)

**Path Aliases:**
- Frontend uses `@/` alias for root — configured in `frontend/tsconfig.json` as `"@/*": ["./*"]`

## Error Handling

**Python patterns:**
- Raise `RuntimeError` for external tool/subprocess failures: `raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr.decode()}")`
- Raise `ValueError` for missing config or invalid input: `raise ValueError("OPENAI_API_KEY is not set")`
- Raise `TimeoutError` for polling timeouts: `raise TimeoutError(f"RunPod STT job {job_id} did not complete within {timeout}s")`
- Log before raising in API callers: `logger.error(...)` then `raise RuntimeError(...)`
- Top-level pipeline errors caught in `backend/app/pipeline.py` `run_job()` via broad `except Exception as exc`
- HTTP status checks: check `resp.is_success` before calling `resp.raise_for_status()`

**TypeScript patterns:**
- `fetch` wrappers check `res.ok` and throw `new Error(...)` with status text
- Component-level: `try/catch` in async handlers, error stored in state and rendered
- Promise chains use `.catch(console.error)` for non-critical failures (e.g., SRT fetch)

## Logging

**Framework:** Python `logging` module, module-level logger per file

**Setup:** `logging.basicConfig` configured in `backend/app/main.py`:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
```

**Per-module logger:** Every Python service file creates `logger = logging.getLogger(__name__)`

**Patterns:**
- Include job ID prefix in messages: `logger.info("[%s] Job started — model=%s", job_id, ...)`
- Use `%`-style formatting (not f-strings) in `logger.*()` calls
- Log before and after long operations (download, transcribe, translate)
- Use `logger.exception()` (not `logger.error()`) in the top-level pipeline catch to include stack trace
- Socket events use `print()` directly — `print(f"Client connected: {sid}")` (not logger)

**Frontend:** `console.error` only for non-critical failures in `.catch(console.error)`

## Comments

**When to Comment:**
- Module-level docstring on all Python service files: `"""Translation engine abstraction — Protocol-based swappable backends."""`
- Function docstrings for public functions in service layer
- Inline comments for non-obvious logic (batch size limit rationale, regex parsing, polling logic)
- Section divider comments in long files to separate class implementations

**No JSDoc/TSDoc** in TypeScript — types are self-documenting via TypeScript interfaces

## Function Design

**Python:**
- Public functions are small and focused (5–20 lines typical)
- Private `_method` helpers for internal batching/formatting logic
- Factory functions (`get_transcription_engine`, `get_translation_engine`) select and construct backends
- `dataclass` used for `TranscriptSegment` — lightweight, no ORM

**TypeScript:**
- Sub-components extracted as local functions within the same file (`YouTubePlayer`, `Html5Player` inside `VideoPlayer.tsx`)
- Async event handlers as named functions inside component body

## Module Design

**Python exports:**
- No `__all__` declarations — all public names implicitly exported
- Factory functions are the primary public interface for service modules
- Protocol classes define the interface contract

**TypeScript exports:**
- Single default export per component file
- Named exports for utility functions in `lib/` files
- Types exported inline (`export type JobState`, `export type ModelConfig`) from page files

## Protocol Pattern (Python)

Services use `typing.Protocol` for swappable backends:
```python
class TranslationEngine(Protocol):
    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]: ...

class TranscriptionEngine(Protocol):
    def transcribe(self, audio_path: Path, src_lang: str) -> list[TranscriptSegment]: ...
```

Factory functions return the protocol type, enabling mock injection via `mock: bool` parameter.

## Mock / Dev Mode

- All service factories accept `mock: bool` parameter controlled by `settings.mock_mode`
- Mock classes (`MockTranscriber`, `MockTranslator`) return static fixtures and sleep 1 second
- `settings.mock_mode` set via `MOCK_MODE=true` environment variable

---

*Convention analysis: 2026-06-17*
