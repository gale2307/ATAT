"""Package audio + transcript data into HuggingFace Dataset format."""
import argparse
import json
from pathlib import Path

from datasets import Audio, Dataset, DatasetDict


def prepare_dataset(audio_dir: Path, transcripts_file: Path, output_dir: Path, eval_split: float = 0.1):
    with open(transcripts_file, encoding="utf-8") as f:
        transcripts = json.load(f)

    # Expect transcripts as list of {audio_id, text}
    records = []
    for item in transcripts:
        audio_path = audio_dir / f"{item['audio_id']}.wav"
        if audio_path.exists():
            records.append({"audio": str(audio_path), "sentence": item["text"]})

    print(f"Found {len(records)} valid audio+transcript pairs")

    dataset = Dataset.from_list(records)
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

    splits = dataset.train_test_split(test_size=eval_split, seed=42)
    dataset_dict = DatasetDict({"train": splits["train"], "eval": splits["test"]})

    dataset_dict.save_to_disk(str(output_dir))
    print(f"Saved dataset to {output_dir}")
    print(f"  Train: {len(dataset_dict['train'])} samples")
    print(f"  Eval:  {len(dataset_dict['eval'])} samples")


def main():
    parser = argparse.ArgumentParser(description="Prepare HuggingFace dataset")
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--transcripts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--eval-split", type=float, default=0.1)
    args = parser.parse_args()

    prepare_dataset(args.audio_dir, args.transcripts, args.output_dir, args.eval_split)


if __name__ == "__main__":
    main()
