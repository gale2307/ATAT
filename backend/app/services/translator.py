"""Translation engine abstraction — Protocol-based swappable backends."""
import logging
import re
import time
from typing import Protocol

import dashscope
import httpx

logger = logging.getLogger(__name__)

from app.config import DOMAINS, LANGUAGE_LABELS, NLLB_LANG_CODES, settings
from app.services.glossary import load_glossary
from app.services.transcriber import TranscriptSegment


class TranslationEngine(Protocol):
    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]: ...


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

_MOCK_TRANSLATIONS = [
    "Faker lands Shockwave with Orianna!",
    "T1 wins the teamfight perfectly.",
    "T1 secures Baron, now heading to close out the game.",
    "Gumayusi's incredible positioning overwhelms the enemy team.",
    "T1 wins! What an incredible game.",
]


class MockTranslator:
    """Returns static English translations without calling any API."""

    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        time.sleep(1)
        return [
            TranscriptSegment(start=s.start, end=s.end, text=_MOCK_TRANSLATIONS[i % len(_MOCK_TRANSLATIONS)])
            for i, s in enumerate(segments)
        ]


# ---------------------------------------------------------------------------
# Qwen-MT (DashScope API)
# ---------------------------------------------------------------------------

class QwenMTEngine:
    """Qwen-MT translation via DashScope SDK with domain glossary injection."""

    def __init__(self, domain: str = "general", src_lang: str = "ko", tgt_lang: str = "en"):
        dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        self._api_key = settings.qwen_mt_api_key
        self._src_lang = LANGUAGE_LABELS.get(src_lang, src_lang)
        self._tgt_lang = LANGUAGE_LABELS.get(tgt_lang, tgt_lang)
        self._glossary = load_glossary(domain)

    # Max segments per API call. 50 can exceed Qwen-MT's output token limit for
    # longer segments, causing the last lines to be silently dropped. 20 keeps
    # both input and output well within limits (~3 calls per typical video).
    _BATCH_SIZE = 30

    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        results = []
        for i in range(0, len(segments), self._BATCH_SIZE):
            batch = segments[i : i + self._BATCH_SIZE]
            translated_texts = self._translate_batch([s.text for s in batch])
            for segment, text in zip(batch, translated_texts):
                results.append(TranscriptSegment(start=segment.start, end=segment.end, text=text))
        return results

    def _translate_batch(self, texts: list[str]) -> list[str]:
        """Translate a list of texts in a single API call using numbered lines."""
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        batch_terms = self._terms_for_batch(texts)
        logger.debug("Qwen-MT batch: %d segments, %d glossary terms", len(texts), len(batch_terms))
        translated = self._call_api(numbered, batch_terms)
        logger.debug("Qwen-MT raw response:\n%s", translated)

        # Only accept lines that match the numbering pattern — ignores blank lines,
        # model commentary, and newlines embedded in a translated sentence.
        lines = [
            m.group(1).strip()
            for line in translated.splitlines()
            if (m := re.match(r"^\d+\.\s+(.*)", line.strip()))
        ]

        if len(lines) < len(texts):
            missing = texts[len(lines):]
            logger.warning(
                "Qwen-MT returned fewer lines than expected (%d/%d) — padding with source text: %s",
                len(lines), len(texts), missing,
            )
            lines.extend(missing)
        elif len(lines) > len(texts):
            extra = lines[len(texts):]
            logger.warning(
                "Qwen-MT returned more lines than expected (%d/%d) — truncating extra: %s",
                len(lines), len(texts), extra,
            )
            lines = lines[:len(texts)]

        return lines

    def _terms_for_batch(self, texts: list[str]) -> list[dict]:
        """Return only glossary terms whose source appears in the current batch."""
        combined = " ".join(texts)
        return [
            {"source": k, "target": v}
            for k, v in self._glossary.items()
            if k in combined
        ]

    def _call_api(self, text: str, terms: list[dict]) -> str:
        translation_options: dict = {
            "source_lang": self._src_lang,
            "target_lang": self._tgt_lang,
        }
        if terms:
            translation_options["terms"] = terms

        response = dashscope.Generation.call(
            api_key=self._api_key,
            model="qwen-mt-flash",
            messages=[{"role": "user", "content": text}],
            translation_options=translation_options,
            result_format="message",
        )
        if response.status_code != 200:
            logger.error(
                "Qwen-MT error: status=%s code=%s message=%s",
                response.status_code,
                response.code,
                response.message,
            )
            raise RuntimeError(f"Qwen-MT API error {response.status_code}: {response.message}")
        return response.output.choices[0].message.content


# ---------------------------------------------------------------------------
# NLLB-200 (self-hosted RunPod worker)
# ---------------------------------------------------------------------------

class NLLBEngine:
    """Self-hosted NLLB-200 translation via GPU worker endpoint."""

    def __init__(self, domain: str = "general", src_lang: str = "ko", tgt_lang: str = "en"):
        self._src_lang = NLLB_LANG_CODES.get(src_lang, "kor_Hang")
        self._tgt_lang = NLLB_LANG_CODES.get(tgt_lang, "eng_Latn")

    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        texts = [s.text for s in segments]
        resp = httpx.post(
            settings.translation_worker_url,
            json={"texts": texts, "src_lang": self._src_lang, "tgt_lang": self._tgt_lang},
            headers={"Authorization": f"Bearer {settings.runpod_api_key}"},
            timeout=120,
        )
        if not resp.is_success:
            logger.error("NLLB worker error: status=%s body=%s", resp.status_code, resp.text)
        resp.raise_for_status()
        return [
            TranscriptSegment(start=s.start, end=s.end, text=t)
            for s, t in zip(segments, resp.json()["translations"])
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_translation_engine(
    engine_id: str,
    domain: str = "general",
    src_lang: str = "ko",
    tgt_lang: str = "en",
    mock: bool = False,
) -> TranslationEngine:
    if mock:
        return MockTranslator()
    engines = {
        "qwen-mt": QwenMTEngine,
        "nllb-600m": NLLBEngine,
        "nllb-3.3b": NLLBEngine,
    }
    cls = engines.get(engine_id, QwenMTEngine)
    return cls(domain=domain, src_lang=src_lang, tgt_lang=tgt_lang)
