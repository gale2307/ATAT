"""Audio extraction from YouTube URLs using yt-dlp."""
import subprocess
from pathlib import Path

from app.config import settings
import yt_dlp


def download_audio(url: str, job_id: str) -> Path:
    """Download audio from a YouTube URL and return the path to the extracted audio file."""
    output_dir = Path(settings.storage_path) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / "audio.%(ext)s"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(audio_path),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        # Required for full YouTube support
        "extractor_args": {"youtube": {"skip": ["hls", "dash"]}},
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "video")

    wav_path = output_dir / "audio.wav"
    return wav_path, title


def download_video(url: str, job_id: str) -> tuple[Path, str]:
    """Download the best video+audio stream and return the path to the mp4 file."""
    output_dir = Path(settings.storage_path) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_dir / "video.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "video")

    return output_dir / "video.mp4", title


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Extract full audio track from a video file as a WAV."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(output_path), "-y"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr.decode()}")
    return output_path


def download_hls_audio(url: str, job_id: str) -> Path:
    """Download HLS livestream audio chunks for real-time processing."""
    output_dir = Path(settings.storage_path) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "stream.%(ext)s"),
        "hls_use_mpegts": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    return output_dir / "stream.ts"
