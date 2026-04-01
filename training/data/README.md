# Training Data

## Sources

- **LCK VOD audio**: Downloaded via `scripts/download_vods.py` using yt-dlp. Audio extracted as 16kHz mono WAV.
- **YouTube auto-captions**: Extracted via `scripts/extract_captions.py` as weak supervision signal (noisy but abundant).
- **Synthetic TTS**: Generated via `scripts/generate_synthetic.py` using Korean TTS on LoL glossary sentences.
- **Manual corrections**: Human-verified segments stored in `corrected/`.

## File format

STT training data (HuggingFace datasets format):
```json
{"audio": {"path": "audio/001.wav", "sampling_rate": 16000}, "sentence": "페이커가 오리아나로 쇼크웨이브를 적중시킵니다"}
```

Translation pairs (`lol_ko_en.json`):
```json
{"korean": "...", "english": "..."}
```

## Data splits

- `processed/train/`: ~80% of data
- `processed/eval/`: ~20% of data
- `processed/test/`: held-out test set (never seen during training)

## Notes

- Audio segments must be ≤30 seconds (Whisper encoder limit)
- Target sampling rate: 16kHz mono
- Minimum segment length: 0.5 seconds
