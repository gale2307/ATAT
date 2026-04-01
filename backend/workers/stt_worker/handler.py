"""RunPod Serverless handler for faster-whisper STT."""
import base64
import tempfile
from pathlib import Path

import runpod
from faster_whisper import WhisperModel

# Load model once at cold start — cached for all subsequent requests
MODEL = WhisperModel("medium", device="cuda", compute_type="float16")


def handler(event):
    """Transcribe audio and return timestamped segments.

    Input:
        audio_b64 (str): base64-encoded WAV bytes
        src_lang  (str): BCP-47 language code, e.g. "ko" (default)

    Output:
        segments: list of {start: float, end: float, text: str}
    """
    audio_b64 = event["input"]["audio_b64"]
    src_lang = event["input"].get("src_lang", "ko")

    audio_bytes = base64.b64decode(audio_b64)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = Path(f.name)

    try:
        segments, _ = MODEL.transcribe(
            str(tmp_path),
            language=src_lang,
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        result = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"segments": result}


runpod.serverless.start({"handler": handler})
