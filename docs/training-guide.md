# Training guide

## Overview

Two models to fine-tune:
1. **Whisper large-v3** (STT) — Korean speech → Korean text, optimized for LoL terminology
2. **NLLB-200** (translation) — Korean text → English text, optimized for LoL domain

Both use LoRA / parameter-efficient fine-tuning to keep GPU requirements low.

## Whisper LoRA fine-tuning

### Prerequisites

```bash
pip install transformers peft bitsandbytes accelerate datasets evaluate jiwer
pip install librosa soundfile
pip install wandb  # experiment tracking
```

### LoRA configuration

```python
from peft import LoraConfig

lora_config = LoraConfig(
    r=32,                    # rank: controls adapter capacity
    lora_alpha=64,           # scaling factor
    target_modules=[         # which layers to adapt
        "q_proj", "v_proj", "k_proj",
        "out_proj", "fc1", "fc2"
    ],
    lora_dropout=0.05,
    bias="none"
)
```

### Key hyperparameters

- **Learning rate**: Use 40x smaller than pre-training rate. For large-v3: ~1e-5 to 5e-5
- **Batch size**: Effective batch size of 16-32 (use gradient accumulation if VRAM limited)
- **Epochs**: 3-10 (use early stopping based on validation WER)
- **Audio segment length**: 1-30 seconds (Whisper's encoder limit)
- **Max label tokens**: 448 (Whisper's decoder limit)

### Training data requirements

**Minimum viable**: ~4-5 hours of corrected audio → noticeable improvement on domain terms
**Good results**: 10-30 hours
**Excellent results**: 50+ hours (including synthetic augmentation)

### Data preparation format

Each sample needs:
- Audio file (WAV, 16kHz mono)
- Correct transcription (Korean text)

HuggingFace Dataset format:
```python
from datasets import Dataset, Audio

dataset = Dataset.from_dict({
    "audio": ["/path/to/clip1.wav", "/path/to/clip2.wav", ...],
    "transcription": ["오리아나가 쇼크웨이브를 사용합니다", ...]
})
dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
```

### Data collection strategies

**Strategy A: Mine existing VODs with corrections**
1. Download LCK VOD audio: `yt-dlp -f bestaudio -x --audio-format wav <LCK_VOD_URL>`
2. Extract YouTube auto-generated Korean subtitles: `yt-dlp --write-auto-sub --sub-lang ko --skip-download <URL>`
3. Run base Whisper on audio to get draft transcriptions
4. Manually correct domain-specific errors (champion names, abilities, items)
5. Segment into 5-30 second clips aligned with subtitle timestamps

**Strategy B: Synthetic data via TTS**
1. Compile LoL glossary (all champions, items, abilities, player names)
2. Use an LLM to generate realistic Korean caster sentences containing these terms
3. Synthesize with multi-speaker TTS (Kokoro-TTS, Coqui TTS)
4. Add noise augmentation (crowd noise, caster overlap) for realism

**Strategy C: Hybrid (recommended)**
- Mix real VOD audio (Strategy A) with synthetic data (Strategy B)
- Real data teaches acoustic patterns; synthetic data ensures vocabulary coverage
- Use appropriate sampling weights (e.g., 70% real, 30% synthetic)

### Training script (Colab notebook)

```python
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer
from peft import get_peft_model, LoraConfig
import torch

# Load base model
model = WhisperForConditionalGeneration.from_pretrained(
    "openai/whisper-large-v3",
    torch_dtype=torch.float16,
    load_in_8bit=True,  # for T4 16GB VRAM
)
processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Expected: ~0.5-1% of total parameters

# Training arguments
training_args = Seq2SeqTrainingArguments(
    output_dir="./whisper-lol-ko-lora",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,  # effective batch = 16
    learning_rate=1e-5,
    num_train_epochs=5,
    evaluation_strategy="steps",
    eval_steps=200,
    save_steps=200,
    logging_steps=50,
    fp16=True,
    predict_with_generate=True,
    generation_max_length=448,
    load_best_model_at_end=True,
    metric_for_best_model="wer",
    greater_is_better=False,
    push_to_hub=True,
    hub_model_id="your-username/whisper-lol-ko-lora",
)

# Train
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=data_collator,
    compute_metrics=compute_wer_metrics,
    tokenizer=processor.feature_extractor,
)
trainer.train()

# Push LoRA adapter to Hub (~60MB)
model.push_to_hub("your-username/whisper-lol-ko-lora")
```

### Evaluation

```python
from evaluate import load
wer_metric = load("wer")

# Test on LoL-specific test set
# Compare base Whisper WER vs fine-tuned WER
# Pay special attention to domain term accuracy:
# - Champion name recognition rate
# - Ability name recognition rate
# - Player IGN recognition rate
```

### Preventing catastrophic forgetting

When fine-tuning, the model can lose general Korean ability. Mitigations:
- LoRA inherently preserves base weights (only adapters change)
- Can disable LoRA adapter at inference time for non-LoL content: `model.disable_adapter()`
- Mix some general Korean speech data into training set (10-20%)

## NLLB-200 fine-tuning

### Prerequisites

```bash
pip install transformers datasets sentencepiece
pip install sacrebleu  # for BLEU evaluation
```

### Data format

Parallel Korean→English sentence pairs in CSV or HuggingFace Dataset:

```csv
korean,english
"오리아나가 쇼크웨이브를 사용합니다","Orianna uses Shockwave"
"페이커가 갱킹을 당했습니다","Faker got ganked"
"드래곤 소울을 획득했습니다","They secured Dragon Soul"
```

### Data sources for parallel LoL data

1. **Riot Games patch notes** — Published in both Korean and English
2. **LoL Wiki** — Champion descriptions, ability descriptions in both languages
3. **Bilingual LCK broadcasts** — Align Korean and English caster transcripts by timestamp
4. **LLM-generated parallel data** — Use GPT-4o/Claude to generate Korean LoL sentences with English translations

### Training

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Trainer, TrainingArguments

model_name = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(model_name, src_lang="kor_Hang", tgt_lang="eng_Latn")
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

training_args = TrainingArguments(
    output_dir="./nllb-lol-ko-en",
    per_device_train_batch_size=8,
    learning_rate=2e-5,
    num_train_epochs=10,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    fp16=True,
    push_to_hub=True,
)

# Train
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_eval,
)
trainer.train()
```

### Evaluation metrics

- **BLEU** (bilingual evaluation understudy): n-gram overlap with reference translations
- **chrF++**: Character-level F-score, often better for morphologically rich languages
- **COMET**: Neural evaluation metric, correlates best with human judgment
- **Domain-specific accuracy**: Percentage of LoL terms correctly translated (custom metric)

## Training workflow

```
1. Laptop: Collect data (yt-dlp VODs, scrape patch notes, generate synthetic)
2. Laptop: Clean + prepare dataset, upload to HuggingFace Hub
3. Colab/Vast.ai: Run Whisper LoRA training notebook
4. Colab/Vast.ai: Run NLLB fine-tuning notebook
5. Both push checkpoints to HuggingFace Hub
6. Inference workers pull new checkpoints on next cold start
7. Evaluate on test set, iterate on data quality
```
