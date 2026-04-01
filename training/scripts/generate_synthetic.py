"""Generate synthetic Korean TTS training data from LoL glossary sentences."""
import argparse
import json
import uuid
from pathlib import Path


def generate_synthetic(glossary_file: Path, output_dir: Path, num_samples: int = 500):
    """Generate TTS audio from LoL terminology sentences.

    Requires a Korean TTS library. Recommended: kokoro-tts or edge-tts.
    Install: pip install edge-tts
    """
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("Install edge-tts: pip install edge-tts")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(glossary_file, encoding="utf-8") as f:
        glossary = json.load(f)

    # Build sentences from glossary terms
    sentences = []
    for ko_term, en_term in glossary.items():
        sentences.append(f"{ko_term}!")
        sentences.append(f"{ko_term}를 사용합니다.")
        sentences.append(f"훌륭한 {ko_term} 플레이입니다!")

    sentences = sentences[:num_samples]

    records = []

    async def synthesize_all():
        for i, text in enumerate(sentences):
            audio_id = str(uuid.uuid4())[:8]
            audio_path = output_dir / f"{audio_id}.mp3"

            communicate = edge_tts.Communicate(text, voice="ko-KR-SunHiNeural")
            await communicate.save(str(audio_path))

            records.append({"audio_id": audio_id, "text": text})
            if i % 50 == 0:
                print(f"Generated {i}/{len(sentences)} samples...")

    asyncio.run(synthesize_all())

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(records)} synthetic samples to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic TTS training data")
    parser.add_argument("--glossary", type=Path, default=Path("data/lol_ko_en.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/synthetic"))
    parser.add_argument("--num-samples", type=int, default=500)
    args = parser.parse_args()

    generate_synthetic(args.glossary, args.output_dir, args.num_samples)


if __name__ == "__main__":
    main()
