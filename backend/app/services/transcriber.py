"""STT engine abstraction — Protocol-based swappable backends."""
import base64
import json
import logging
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

import httpx
from faster_whisper import WhisperModel

from app.config import STT_MODELS, settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


class TranscriptionEngine(Protocol):
    def transcribe(self, audio_path: Path, src_lang: str) -> list[TranscriptSegment]: ...


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

_MOCK_SEGMENTS = [
    TranscriptSegment(start=0.0,  end=3.5,  text="페이커가 오리아나로 쇼크웨이브를 적중시킵니다!"),
    TranscriptSegment(start=3.5,  end=7.0,  text="T1이 팀파이트를 완벽하게 승리했습니다."),
    TranscriptSegment(start=7.0,  end=11.5, text="바론을 획득한 T1, 이제 게임을 마무리지으러 갑니다."),
    TranscriptSegment(start=11.5, end=15.0, text="구마유시의 뛰어난 포지셔닝으로 적팀을 압도합니다."),
    TranscriptSegment(start=15.0, end=19.5, text="T1 승리! 정말 놀라운 경기였습니다."),
]


class MockTranscriber:
    """Returns static Korean segments without loading any model."""

    def transcribe(self, audio_path: Path, src_lang: str = "ko") -> list[TranscriptSegment]:
        time.sleep(1)
        return list(_MOCK_SEGMENTS)


# ---------------------------------------------------------------------------
# Local faster-whisper
# ---------------------------------------------------------------------------

_WHISPER_MODEL_MAP = {
    "whisper-large-v3": "large-v3",
    "whisper-large-v3-turbo": "large-v3-turbo",
    "whisper-medium": "medium",
    "whisper-large-v3-lol": "large-v3",  # TODO: load LoRA from HF_STT_MODEL_REPO
}


class LocalWhisperTranscriber:
    """Local faster-whisper inference (CPU, int8)."""

    def __init__(self, model_id: str = "whisper-large-v3"):
        model_size = _WHISPER_MODEL_MAP.get(model_id, "large-v3")
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: Path, src_lang: str = "ko") -> list[TranscriptSegment]:
        segments, _ = self._model.transcribe(
            str(audio_path),
            language=src_lang,
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        return [TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]

    def transcribe_stream(self, audio_path: Path, src_lang: str = "ko") -> Iterator[TranscriptSegment]:
        """Yield segments one at a time as they complete."""
        segments, _ = self._model.transcribe(str(audio_path), language=src_lang, task="transcribe")
        for s in segments:
            yield TranscriptSegment(start=s.start, end=s.end, text=s.text.strip())


# ---------------------------------------------------------------------------
# GPT-4o Transcribe (OpenAI API)
# ---------------------------------------------------------------------------

_OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
_OPENAI_MAX_BYTES = 25 * 1024 * 1024


def _audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


class GPT4oTranscriber:
    """OpenAI GPT-4o Transcribe API. Converts audio to 16kHz mono MP3 before upload."""

    def __init__(self, api_key: str = ""):
        if not api_key:
            api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self._api_key = api_key

    def transcribe(self, audio_path: Path, src_lang: str = "ko") -> list[TranscriptSegment]:
        mp3_path = self._to_mp3(audio_path)
        try:
            duration = _audio_duration(mp3_path)
            return self._call_api(mp3_path, src_lang, duration)
        finally:
            mp3_path.unlink(missing_ok=True)

    def _to_mp3(self, audio_path: Path) -> Path:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            mp3_path = Path(tmp.name)
        result = subprocess.run(
            ["ffmpeg", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-b:a", "128k", str(mp3_path), "-y"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")
        if mp3_path.stat().st_size > _OPENAI_MAX_BYTES:
            mp3_path.unlink(missing_ok=True)
            raise ValueError(f"Audio exceeds OpenAI 25 MB limit after MP3 conversion: {audio_path}")
        return mp3_path

    def _call_api(self, mp3_path: Path, src_lang: str, duration: float) -> list[TranscriptSegment]:
        with open(mp3_path, "rb") as f:
            response = httpx.post(
                _OPENAI_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                data={"model": "gpt-4o-transcribe", "language": src_lang, "response_format": "json"},
                files={"file": (mp3_path.name, f, "audio/mpeg")},
                timeout=300,
            )
        if not response.is_success:
            logger.error("OpenAI transcription error: status=%s body=%s", response.status_code, response.text)
        response.raise_for_status()

        text = response.json().get("text", "").strip()
        sentences = _split_sentences(text)
        if not sentences:
            return [TranscriptSegment(start=0.0, end=duration, text=text)]

        interval = duration / len(sentences)
        return [
            TranscriptSegment(start=i * interval, end=(i + 1) * interval, text=s)
            for i, s in enumerate(sentences)
        ]


# ---------------------------------------------------------------------------
# RunPod Serverless faster-whisper worker
# ---------------------------------------------------------------------------

class RunPodTranscriber:
    """Sends audio to a RunPod Serverless faster-whisper worker. Returns real timestamps."""

    def __init__(self, model_id: str = "whisper-medium"):
        if not settings.stt_worker_url:
            raise ValueError("STT_WORKER_URL is not set")
        self._url = settings.stt_worker_url
        self._api_key = settings.runpod_api_key
        self._model_id = model_id

    def transcribe(self, audio_path: Path, src_lang: str = "ko") -> list[TranscriptSegment]:
        audio_b64 = base64.b64encode(audio_path.read_bytes()).decode()
        job_id = self._submit(audio_b64, src_lang)
        logger.info("RunPod STT job submitted: %s", job_id)
        output = self._poll(job_id)
        return [
            TranscriptSegment(start=s["start"], end=s["end"], text=s["text"])
            for s in output["segments"]
        ]

    def _submit(self, audio_b64: str, src_lang: str) -> str:
        """POST to /run and return the RunPod job ID."""
        run_url = self._url.replace("/runsync", "/run")
        resp = httpx.post(
            run_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"input": {"audio_b64": audio_b64, "src_lang": src_lang, "model_id": self._model_id}},
            timeout=httpx.Timeout(connect=10, write=300, read=30, pool=5),
        )
        if not resp.is_success:
            logger.error("RunPod STT submit error: status=%s body=%s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()["id"]

    def _poll(self, job_id: str, timeout: int = 600, interval: int = 5) -> dict:
        """Poll /status/{job_id} until COMPLETED or FAILED."""
        base = self._url.replace("/runsync", "").replace("/run", "")
        status_url = f"{base}/status/{job_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        elapsed = 0
        while elapsed < timeout:
            time.sleep(interval)
            elapsed += interval
            resp = httpx.get(status_url, headers=headers, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            status = body.get("status")
            logger.info("RunPod STT job %s: status=%s elapsed=%ds", job_id, status, elapsed)
            if status == "COMPLETED":
                return body["output"]
            if status == "FAILED":
                error = body.get("error", "unknown error")
                logger.error("RunPod STT job %s failed: %s", job_id, error)
                raise RuntimeError(f"RunPod STT worker failed: {error}")
        raise TimeoutError(f"RunPod STT job {job_id} did not complete within {timeout}s")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_transcription_engine(model_id: str, mock: bool = False) -> TranscriptionEngine:
    if mock:
        return MockTranscriber()
    if model_id == "gpt-4o-transcribe":
        return GPT4oTranscriber()
    model_cfg = STT_MODELS.get(model_id)
    if model_cfg:
        if model_cfg["type"] == "runpod":
            return RunPodTranscriber(model_id)
    return LocalWhisperTranscriber(model_id)
