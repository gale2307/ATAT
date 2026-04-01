"""FFmpeg subtitle burn-in and video packaging."""
import subprocess
from pathlib import Path


def burn_subtitles(video_path: Path, subtitle_path: Path, output_path: Path) -> Path:
    """Burn SRT subtitles into video using FFmpeg."""
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"subtitles={subtitle_path}",
        "-c:a", "copy",
        "-y",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    return output_path


def extract_audio_segment(video_path: Path, start: float, duration: float, output_path: Path) -> Path:
    """Extract a segment of audio from a video file."""
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-t", str(duration),
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-y",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    return output_path
