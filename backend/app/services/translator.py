"""Translation engine abstraction (Protocol-based swappable backends)."""
import logging
import time
from typing import Protocol

import dashscope
import httpx

logger = logging.getLogger(__name__)

from app.config import DOMAINS, LANGUAGE_LABELS, NLLB_LANG_CODES, settings
from app.services.glossary import load_glossary
from app.services.transcriber import TranscriptSegment


def _get_system_prompt(domain: str, src_lang: str, tgt_lang: str) -> str:
    src_label = LANGUAGE_LABELS.get(src_lang, src_lang)
    tgt_label = LANGUAGE_LABELS.get(tgt_lang, tgt_lang)
    domain_cfg = next((d for d in DOMAINS if d["id"] == domain), DOMAINS[0])
    return domain_cfg["system_prompt"].format(src_lang=src_label, tgt_lang=tgt_label)


_MOCK_TRANSLATIONS = [
    "Faker lands Shockwave with Orianna!",
    "T1 wins the teamfight perfectly.",
    "T1 secures Baron, now heading to close out the game.",
    "Gumayusi's incredible positioning overwhelms the enemy team.",
    "T1 wins! What an incredible game.",
]


class MockEngine:
    """Returns static English translations without calling any API."""

    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        time.sleep(1)  # simulate processing time
        return [
            TranscriptSegment(start=s.start, end=s.end, text=_MOCK_TRANSLATIONS[i % len(_MOCK_TRANSLATIONS)])
            for i, s in enumerate(segments)
        ]


class TranslationEngine(Protocol):
    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]: ...


class QwenMTEngine:
    """Qwen-MT translation via DashScope SDK with domain glossary injection."""

    def __init__(self, domain: str = "general", src_lang: str = "ko", tgt_lang: str = "en"):
        dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
        self.api_key = settings.qwen_mt_api_key
        self.src_lang = LANGUAGE_LABELS.get(src_lang, src_lang)
        self.tgt_lang = LANGUAGE_LABELS.get(tgt_lang, tgt_lang)
        self.glossary = load_glossary(domain)

    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(start=s.start, end=s.end, text=self._translate_text(s.text))
            for s in segments
        ]

    def _translate_text(self, text: str) -> str:
        response = dashscope.Generation.call(
            api_key=self.api_key,
            model="qwen-mt-flash",
            messages=[{"role": "user", "content": text}],
            translation_options={
                "source_lang": self.src_lang,
                "target_lang": self.tgt_lang,
                "terms": [{"source": k, "target": v} for k, v in list(self.glossary.items())[:50]],
            },
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


class NLLBEngine:
    """Self-hosted NLLB-200 translation via GPU worker endpoint."""

    def __init__(self, domain: str = "general", src_lang: str = "ko", tgt_lang: str = "en"):
        self.src_lang = NLLB_LANG_CODES.get(src_lang, "kor_Hang")
        self.tgt_lang = NLLB_LANG_CODES.get(tgt_lang, "eng_Latn")

    def translate(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        texts = [s.text for s in segments]
        resp = httpx.post(
            settings.translation_worker_url,
            json={"texts": texts, "src_lang": self.src_lang, "tgt_lang": self.tgt_lang},
            headers={"Authorization": f"Bearer {settings.runpod_api_key}"},
            timeout=120,
        )
        if not resp.is_success:
            logger.error("NLLB worker error: status=%s body=%s", resp.status_code, resp.text)
        resp.raise_for_status()
        results = resp.json()["translations"]
        return [
            TranscriptSegment(start=s.start, end=s.end, text=t)
            for s, t in zip(segments, results)
        ]


def get_translation_engine(
    engine_id: str,
    domain: str = "general",
    src_lang: str = "ko",
    tgt_lang: str = "en",
    mock: bool = False,
) -> TranslationEngine:
    if mock:
        return MockEngine()
    engines = {
        "qwen-mt": QwenMTEngine,
        "nllb-600m": NLLBEngine,
        "nllb-3.3b": NLLBEngine,
    }
    cls = engines.get(engine_id, QwenMTEngine)
    return cls(domain=domain, src_lang=src_lang, tgt_lang=tgt_lang)
