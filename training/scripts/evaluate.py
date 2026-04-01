"""Evaluate Whisper model WER on LoL-specific test set."""
import argparse
import json
from pathlib import Path

import evaluate
from datasets import Audio, Dataset
from faster_whisper import WhisperModel

wer_metric = evaluate.load("wer")


def evaluate_model(model_id: str, test_file: Path, device: str = "cpu") -> dict:
    with open(test_file, encoding="utf-8") as f:
        test_data = json.load(f)

    model = WhisperModel(model_id, device=device, compute_type="int8" if device == "cpu" else "float16")

    references = []
    hypotheses = []

    for item in test_data:
        audio_path = item["audio_path"]
        reference = item["text"]

        segments, _ = model.transcribe(audio_path, language="ko", task="transcribe")
        hypothesis = " ".join(s.text.strip() for s in segments)

        references.append(reference)
        hypotheses.append(hypothesis)

    wer = wer_metric.compute(predictions=hypotheses, references=references)
    print(f"WER: {wer:.4f} ({wer*100:.2f}%)")

    return {"wer": wer, "num_samples": len(references)}


def main():
    parser = argparse.ArgumentParser(description="Evaluate Whisper WER")
    parser.add_argument("--model", required=True, help="Model ID or path")
    parser.add_argument("--test-file", type=Path, required=True, help="JSON test file")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = parser.parse_args()

    results = evaluate_model(args.model, args.test_file, args.device)

    output_file = Path(f"eval_results_{args.model.replace('/', '_')}.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
