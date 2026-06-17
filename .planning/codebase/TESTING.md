# Testing Patterns

**Analysis Date:** 2026-06-17

## Test Framework

**Runner:**
- Python: `pytest` + `pytest-asyncio` — declared in `backend/pyproject.toml` under `[project.optional-dependencies] dev`
- TypeScript: No test framework configured — `package.json` has no test script and no Jest/Vitest dependency

**Assertion Library:**
- Python: pytest built-in assertions
- TypeScript: Not configured

**Run Commands:**
```bash
# Python backend (from backend/)
pip install -e ".[dev]"
pytest                    # Run all tests

# Frontend
# No test runner configured
```

## Test File Organization

**Current state:**
- No test files exist in the codebase. The `tests/` directory is absent from both `backend/` and `frontend/`.
- Test infrastructure is declared (`pytest`, `pytest-asyncio`, `httpx` in dev deps) but no tests have been written.

**Intended location (based on pyproject.toml dev deps):**
- Python tests: `backend/tests/` (standard pytest discovery)
- Test files should be named `test_*.py`

## Test Structure

**No existing tests to reference.** Based on declared dependencies and codebase patterns, the intended approach is:

```python
# Intended pytest pattern
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_job():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/jobs", json={
            "url": "https://youtube.com/watch?v=test",
            "stt_model": "whisper-large-v3",
        })
    assert response.status_code == 200
```

## Mocking

**Mock infrastructure exists in production code** — not in test files:

- `backend/app/services/transcriber.py`: `MockTranscriber` class returns `_MOCK_SEGMENTS` (5 hardcoded Korean segments with timestamps)
- `backend/app/services/translator.py`: `MockTranslator` class returns `_MOCK_TRANSLATIONS` (5 hardcoded English strings)
- Controlled via `settings.mock_mode` (env var `MOCK_MODE=true`) — all factory functions check this flag

**Mock activation:**
```python
# In backend/app/services/transcriber.py
def get_transcription_engine(model_id: str, mock: bool = False) -> TranscriptionEngine:
    if mock:
        return MockTranscriber()
    ...

# In backend/app/services/translator.py
def get_translation_engine(engine_id, domain, src_lang, tgt_lang, mock: bool = False) -> TranslationEngine:
    if mock:
        return MockTranslator()
    ...
```

**What to mock in tests:**
- External API calls (`dashscope.Generation.call`, `httpx.post` to RunPod/OpenAI)
- `yt_dlp.YoutubeDL` — requires network and binary ffmpeg
- `subprocess.run` — ffmpeg calls
- `WhisperModel` — requires model download

**What NOT to mock:**
- `TranscriptSegment` dataclass — pure data, no side effects
- `generate_srt` / `generate_vtt` — pure file I/O, can use `tmp_path` fixture
- `load_glossary` — reads JSON files, can use real files in tests
- SQLModel database — use in-memory SQLite for integration tests

## Fixtures and Factories

**No test fixtures written yet.** Recommended patterns based on existing code:

```python
# Suggested fixtures
import pytest
from pathlib import Path

@pytest.fixture
def mock_audio_path(tmp_path) -> Path:
    """Create a minimal WAV file for testing."""
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    return wav

@pytest.fixture
def mock_segments():
    from app.services.transcriber import TranscriptSegment
    return [
        TranscriptSegment(start=0.0, end=3.5, text="Test segment one"),
        TranscriptSegment(start=3.5, end=7.0, text="Test segment two"),
    ]
```

**Existing mock data (usable in tests):**
- `_MOCK_SEGMENTS` in `backend/app/services/transcriber.py` — 5 Korean segments
- `_MOCK_TRANSLATIONS` in `backend/app/services/translator.py` — 5 English strings

## Coverage

**Requirements:** None enforced (no coverage config in `pyproject.toml`)

**View Coverage:**
```bash
pytest --cov=app --cov-report=html
```

## Test Types

**Unit Tests (intended):**
- `generate_srt` and `generate_vtt` in `backend/app/services/subtitle.py` — pure functions, no dependencies
- `load_glossary` in `backend/app/services/glossary.py` — reads JSON files
- `_format_srt_time` and `_format_vtt_time` — pure time formatting
- `parseSrt` and `parseSrtTime` in `frontend/components/VideoPlayer.tsx` — pure string parsing

**Integration Tests (intended):**
- FastAPI endpoints via `httpx.AsyncClient` — `httpx` is in dev deps for this purpose
- Pipeline `run_job()` with `mock_mode=True` to avoid real API calls

**E2E Tests:**
- Not configured

## Key Testable Units (No Tests Exist)

These are the highest-value units to test, in priority order:

1. `backend/app/services/subtitle.py` — `generate_srt()`, `generate_vtt()` — pure functions, easy to test
2. `backend/app/services/glossary.py` — `load_glossary()` — file I/O, use real domain JSON files
3. `backend/app/routers/jobs.py` — REST endpoints — use `httpx.AsyncClient` with in-memory DB
4. `backend/app/services/translator.py` — `QwenMTEngine._translate_batch()` line-count mismatch handling (padding/truncating logic)
5. `backend/app/services/transcriber.py` — `_split_sentences()` for GPT-4o fallback

## Notes on Testing Strategy

- The `Protocol`-based design (`TranscriptionEngine`, `TranslationEngine`) makes unit testing straightforward — pass `MockTranscriber`/`MockTranslator` directly without relying on env var
- FastAPI's `BackgroundTasks` in `POST /jobs` spawns `run_job()` asynchronously — integration tests should await the background task or test `run_job()` directly
- SQLModel uses SQLite by default (`atat.db`) — tests should override `DATABASE_URL` to `:memory:`

---

*Testing analysis: 2026-06-17*
