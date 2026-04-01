# Model comparison

## Speech-to-text (STT) models

### Selected: OpenAI Whisper large-v3 (with LoRA fine-tuning)

**Why Whisper**: Most mature fine-tuning ecosystem, excellent Korean support (99+ languages), open source (Apache 2.0), built-in translation mode for Korean→English.

**Whisper model variants**:

| Model | Params | VRAM (full) | VRAM (LoRA) | Speed (vs large) | Korean quality |
|-------|--------|-------------|-------------|-------------------|----------------|
| tiny | 39M | ~1GB | <1GB | 32x | Poor |
| base | 74M | ~1GB | <1GB | 16x | Fair |
| small | 244M | ~2GB | ~2GB | 6x | Good |
| medium | 769M | ~5GB | ~3GB | 2x | Very good |
| large-v3 | 1.5B | ~10GB | ~5GB | 1x | Excellent |
| turbo | 809M | ~6GB | ~4GB | 8x | Good (NO translate task) |

**Important**: Whisper `turbo` does NOT support `--task translate`. For Korean→English translation in a single model, use `medium` or `large`.

**Inference runtime**: Use `faster-whisper` (CTranslate2), not the base `openai-whisper` package. 4x faster, lower memory, supports batched inference and word-level timestamps.

### Alternatives considered

**Deepgram Nova-3**: Best latency (<300ms) but no built-in translation, Korean only in batch mode, not open source, API-only. $0.0077/min.

**Google Chirp 3**: 85+ languages, built-in speech translation via Chirp 2, but expensive ($0.016/min), requires GCP infrastructure.

**Azure Speech Translation**: Purpose-built for real-time speech translation, Korean fully supported, mature SDK. But $2.50/hr, locked to Azure.

**AssemblyAI Universal-3 Pro**: Excellent streaming at $0.15/hr, but Korean only in batch mode (not streaming).

**Meta SeamlessM4T v2**: End-to-end Korean→English, open source, ~2s latency with SeamlessStreaming. But CC BY-NC 4.0 license, needs 40GB+ VRAM, less fine-tuning documentation.

## Translation models

### Primary: Qwen-MT Turbo (API)

- Best Korean→English quality among translation-focused models
- Built-in terminology intervention via `terms` parameter — pass LoL glossary directly in API call
- $0.50/M output tokens (~$0.015 per 3-hour LCK broadcast)
- MoE architecture = fast inference
- Supports domain prompts and translation memory
- 92 languages

**API usage**:
```python
import httpx

response = httpx.post(
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "qwen-mt-turbo",
        "messages": [{"role": "user", "content": korean_text}],
        "translation_options": {
            "source_lang": "Korean",
            "target_lang": "English",
            "terms": [
                {"source": "쇼크웨이브", "target": "Shockwave"},
                {"source": "오리아나", "target": "Orianna"},
                {"source": "갱킹", "target": "ganking"},
                # ... full glossary
            ]
        }
    }
)
```

### Secondary: NLLB-200 (self-hosted, fine-tunable)

- Meta's open-source translation model, 200 languages
- Distilled-600M runs on T4 (~2GB VRAM), 3.3B for better quality
- Korean (kor_Hang) → English (eng_Latn) well supported
- Can fine-tune on LoL domain parallel data (12K+ samples recommended)
- Fast inference (~50ms/sentence on GPU)
- Good for offline/API-free operation

### Tertiary: General LLM with prompt engineering

- GPT-4o-mini, Claude, or Qwen3-8B (self-hosted)
- Highest quality for natural-sounding translations
- Use system prompt with LoL glossary + style instructions
- Most expensive option, best for post-editing or high-quality batch runs

### Translation engine protocol

```python
from typing import Protocol

class TranslationEngine(Protocol):
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str: ...

class QwenMTEngine:
    """Qwen-MT API with LoL glossary injection."""
    ...

class NLLBEngine:
    """Local NLLB-200 inference via HuggingFace transformers."""
    ...

class LLMEngine:
    """General LLM translation via litellm (GPT-4o, Claude, Qwen3)."""
    ...
```

## Cloud GPU options for training

| Platform | GPU | Price/hr | Best for |
|----------|-----|----------|----------|
| Google Colab Pro | T4 (16GB) | ~$0.18 | Iterating, prototyping |
| Google Colab Pro | A100 (40GB) | ~$1.50 | Larger experiments |
| Vast.ai | RTX 4090 (24GB) | ~$0.30 | Budget training runs |
| Vast.ai | A100 (80GB) | ~$0.80 | Long fine-tuning |
| RunPod Community | RTX 4090 (24GB) | ~$0.34 | Reliable training |
| RunPod Community | A100 (80GB) | ~$1.19 | Production fine-tuning |
| Lambda Labs | A100 (80GB) | ~$1.10 | Clean DX, pre-installed |
| Modal | A100 (40GB) | Per-second | Serverless training |

**Recommendation**: Start with Colab Pro ($10/mo) for iterating. Move to Vast.ai/RunPod for longer runs. Whisper LoRA fine-tuning on T4 takes ~6-8 hours for 10hrs of audio data.
