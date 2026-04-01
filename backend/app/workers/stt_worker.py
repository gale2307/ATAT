"""GPU STT worker — runs on RunPod Serverless / Modal.

This module exposes a handler function that receives audio data and returns
Korean transcript segments. Deploy as a serverless endpoint.
"""
import base64
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

# Loaded once at cold start
_model: WhisperModel | None = None


def _load_model(model_id: str = "large-v3") -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(model_id, device="cuda", compute_type="float16")
    return _model


def handler(job: dict) -> dict:
    """RunPod serverless handler.

    Input:
        job["input"]["audio_b64"]: base64-encoded WAV audio
        job["input"]["model_id"]: whisper model variant (optional)

    Output:
        {"segments": [{"start": float, "end": float, "text": str}, ...]}
    """
    input_data = job.get("input", {})
    audio_b64 = input_data["audio_b64"]
    model_id = input_data.get("model_id", "large-v3")

    audio_bytes = base64.b64decode(audio_b64)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = Path(tmp.name)

    model = _load_model(model_id)
    segments, _info = model.transcribe(
        str(tmp_path),
        language="ko",
        task="transcribe",
        beam_size=5,
        vad_filter=True,
    )

    tmp_path.unlink(missing_ok=True)

    return {
        "segments": [
            {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()}
            for s in segments
        ]
    }


if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
