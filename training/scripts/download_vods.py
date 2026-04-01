"""Batch download LCK VOD audio from YouTube using yt-dlp."""
import argparse
import json
from pathlib import Path

import yt_dlp


def download_vods(urls: list[str], output_dir: Path, max_duration: int = 14400):
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
        "match_filter": yt_dlp.utils.match_filter_func(f"duration <= {max_duration}"),
        "writeinfojson": True,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(urls)

    print(f"Downloaded {len(urls)} VODs to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Download LCK VOD audio")
    parser.add_argument("--urls-file", type=Path, required=True, help="JSON file with list of YouTube URLs")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/audio"), help="Output directory")
    parser.add_argument("--max-duration", type=int, default=14400, help="Max video duration in seconds")
    args = parser.parse_args()

    with open(args.urls_file) as f:
        urls = json.load(f)

    download_vods(urls, args.output_dir, args.max_duration)


if __name__ == "__main__":
    main()
