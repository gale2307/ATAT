"""STT engine abstraction — faster-whisper (local) and GPT-4o Transcribe (API)."""
import json
import logging
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import httpx
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

MOCK_SEGMENTS = [
    TranscriptSegment(start=0.0,  end=3.5,  text="페이커가 오리아나로 쇼크웨이브를 적중시킵니다!"),
    TranscriptSegment(start=3.5,  end=7.0,  text="T1이 팀파이트를 완벽하게 승리했습니다."),
    TranscriptSegment(start=7.0,  end=11.5, text="바론을 획득한 T1, 이제 게임을 마무리지으러 갑니다."),
    TranscriptSegment(start=11.5, end=15.0, text="구마유시의 뛰어난 포지셔닝으로 적팀을 압도합니다."),
    TranscriptSegment(start=15.0, end=19.5, text="T1 승리! 정말 놀라운 경기였습니다."),
]


def transcribe_mock() -> list[TranscriptSegment]:
    """Return static segments without loading any model."""
    time.sleep(1)
    return MOCK_SEGMENTS


# ---------------------------------------------------------------------------
# Local faster-whisper
# ---------------------------------------------------------------------------

def get_whisper_model(model_id: str) -> WhisperModel:
    model_map = {
        "whisper-large-v3": "large-v3",
        "whisper-large-v3-turbo": "large-v3-turbo",
        "whisper-medium": "medium",
        "whisper-large-v3-lol": "large-v3-lol",  # TODO: load LoRA from HF_STT_MODEL_REPO
    }
    model_size = model_map.get(model_id, "large-v3")
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe(audio_path: Path, model_id: str = "whisper-large-v3", src_lang: str = "ko") -> list[TranscriptSegment]:
    """Transcribe audio with faster-whisper and return timestamped segments."""
    model = get_whisper_model(model_id)
    segments, _info = model.transcribe(
        str(audio_path),
        language=src_lang,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    return [TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]


def transcribe_chunks(audio_path: Path, model_id: str = "whisper-large-v3", src_lang: str = "ko") -> Iterator[TranscriptSegment]:
    """Streaming transcription — yields segments as they complete."""
    model = get_whisper_model(model_id)
    segments, _info = model.transcribe(str(audio_path), language=src_lang, task="transcribe")
    for s in segments:
        yield TranscriptSegment(start=s.start, end=s.end, text=s.text.strip())


# ---------------------------------------------------------------------------
# GPT-4o Transcribe (OpenAI API)
# ---------------------------------------------------------------------------

OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MAX_BYTES = 25 * 1024 * 1024  # API limit


def _audio_duration(path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _split_sentences(text: str) -> list[str]:
    """Split transcript text on sentence boundaries."""
    parts = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def transcribe_gpt4o(audio_path: Path, src_lang: str = "ko", api_key: str = "") -> list[TranscriptSegment]:
    """Transcribe audio using the OpenAI GPT-4o Transcribe API.

    Returns timestamped segments. Requires OPENAI_API_KEY.
    Audio is converted to 16kHz mono MP3 before upload. Raises if the
    converted file still exceeds the OpenAI 25 MB limit (~26 min at 128kbps).
    """
    if not api_key:
        from app.config import settings
        api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    # Convert to 16kHz mono MP3 — avoids 500s caused by non-standard WAV encodings
    # from yt-dlp (stereo, 48kHz, 32-bit float, etc.)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_path = Path(tmp.name)

    result = subprocess.run(
        ["ffmpeg", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-b:a", "128k", str(mp3_path), "-y"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")

    if mp3_path.stat().st_size > OPENAI_MAX_BYTES:
        mp3_path.unlink(missing_ok=True)
        raise ValueError(f"Audio exceeds OpenAI 25 MB limit even after MP3 conversion: {audio_path}")

    try:
        duration = _audio_duration(mp3_path)
        with open(mp3_path, "rb") as f:
            response = httpx.post(
                OPENAI_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "model": "gpt-4o-transcribe",
                    "language": src_lang,
                    "response_format": "json",
                },
                files={"file": (mp3_path.name, f, "audio/mpeg")},
                timeout=300,
            )
        if not response.is_success:
            logger.error(
                "OpenAI transcription error: status=%s body=%s",
                response.status_code,
                response.text,
            )
        response.raise_for_status()
    finally:
        mp3_path.unlink(missing_ok=True)

    text = response.json().get("text", "").strip()
    sentences = _split_sentences(text)
    if not sentences:
        return [TranscriptSegment(start=0.0, end=duration, text=text)]

    interval = duration / len(sentences)
    return [
        TranscriptSegment(start=i * interval, end=(i + 1) * interval, text=s)
        for i, s in enumerate(sentences)
    ]
