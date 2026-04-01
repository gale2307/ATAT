"""Extract YouTube auto-generated Korean captions as weak supervision."""
import argparse
import json
from pathlib import Path

import yt_dlp


def extract_captions(url: str, output_dir: Path) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "skip_download": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["ko"],
        "subtitlesformat": "srv3",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id")

    vtt_path = output_dir / f"{video_id}.ko.vtt"
    return vtt_path if vtt_path.exists() else None


def vtt_to_segments(vtt_path: Path) -> list[dict]:
    """Parse VTT file into list of {start, end, text} dicts."""
    segments = []
    with open(vtt_path, encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            parts = line.split("-->")
            start = _vtt_time_to_seconds(parts[0].strip())
            end = _vtt_time_to_seconds(parts[1].strip().split()[0])
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = " ".join(text_lines)
            if text:
                segments.append({"start": start, "end": end, "text": text})
        i += 1

    return segments


def _vtt_time_to_seconds(t: str) -> float:
    parts = t.split(":")
    if len(parts) == 3:
        h, m, s = parts
    else:
        h, m, s = 0, parts[0], parts[1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    parser = argparse.ArgumentParser(description="Extract YouTube auto-captions")
    parser.add_argument("--urls-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/captions"))
    args = parser.parse_args()

    with open(args.urls_file) as f:
        urls = json.load(f)

    all_segments = []
    for url in urls:
        vtt_path = extract_captions(url, args.output_dir)
        if vtt_path:
            segments = vtt_to_segments(vtt_path)
            all_segments.extend(segments)
            print(f"Extracted {len(segments)} segments from {url}")

    output_file = args.output_dir / "all_segments.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_segments, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(all_segments)} segments saved to {output_file}")


if __name__ == "__main__":
    main()
