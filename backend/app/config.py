from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API keys
    qwen_mt_api_key: str = ""
    openai_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Storage
    storage_path: str = "/tmp/atat"

    # GPU workers
    runpod_api_key: str = ""
    stt_worker_url: str = ""
    translation_worker_url: str = ""

    # HuggingFace
    hf_token: str = ""
    hf_stt_model_repo: str = ""

    # App
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Local dev
    mock_mode: bool = False

    # Model registry
    default_stt_model: str = "whisper-large-v3"
    default_translation_engine: str = "qwen-mt"
    default_domain: str = "general"
    default_src_lang: str = "ko"
    default_tgt_lang: str = "en"


settings = Settings()

STT_MODELS = [
    {"id": "whisper-large-v3", "label": "Whisper large-v3", "type": "local"},
    {"id": "whisper-large-v3-turbo", "label": "Whisper large-v3-turbo", "type": "local"},
    {"id": "whisper-medium", "label": "Whisper medium", "type": "local"},
    {"id": "whisper-large-v3-lol", "label": "Whisper large-v3 (LoL fine-tuned)", "type": "lora", "domain": "lol-esports"},
    {"id": "gpt-4o-transcribe", "label": "GPT-4o Transcribe (API)", "type": "api"},
]

TRANSLATION_ENGINES = [
    {"id": "qwen-mt", "label": "Qwen-MT Turbo (API)", "type": "api"},
    {"id": "nllb-600m", "label": "NLLB-200 600M (self-hosted)", "type": "local"},
    {"id": "nllb-3.3b", "label": "NLLB-200 3.3B (self-hosted)", "type": "local"},
    {"id": "gpt-4o", "label": "GPT-4o (premium)", "type": "api"},
]

DOMAINS = [
    {
        "id": "general",
        "label": "General",
        "description": "No domain-specific glossary",
        "system_prompt": "You are a professional {src_lang} to {tgt_lang} translator. Translate accurately and naturally.",
    },
    {
        "id": "lol-esports",
        "label": "LoL Esports",
        "description": "League of Legends LCK broadcasts and esports commentary",
        "system_prompt": "You are a {src_lang} to {tgt_lang} translator specializing in League of Legends esports commentary. Preserve champion names, player IGNs, team names, and game terminology.",
    },
    {
        "id": "kpop",
        "label": "K-Pop",
        "description": "Korean pop music content, idol shows, fan cams",
        "system_prompt": "You are a {src_lang} to {tgt_lang} translator specializing in K-Pop content. Preserve artist names, group names, and industry terminology.",
    },
    {
        "id": "kdrama",
        "label": "K-Drama",
        "description": "Korean dramas and variety shows",
        "system_prompt": "You are a {src_lang} to {tgt_lang} translator specializing in Korean dramas. Translate naturally for subtitle display, preserving honorifics context where important.",
    },
    {
        "id": "anime",
        "label": "Anime",
        "description": "Japanese animation and manga adaptations",
        "system_prompt": "You are a {src_lang} to {tgt_lang} translator specializing in anime. Preserve character names, attack names, and genre-specific terminology.",
    },
    {
        "id": "tech",
        "label": "Tech / Dev",
        "description": "Technology, programming, and developer content",
        "system_prompt": "You are a {src_lang} to {tgt_lang} translator specializing in technology and software development content. Keep technical terms, product names, and acronyms accurate.",
    },
]

# NLLB-200 language codes keyed by BCP-47 code
NLLB_LANG_CODES: dict[str, str] = {
    "ko": "kor_Hang",
    "ja": "jpn_Jpan",
    "zh": "zho_Hans",
    "zh-tw": "zho_Hant",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "ar": "arb_Arab",
    "en": "eng_Latn",
}

LANGUAGE_PAIRS = [
    {"src": "ko", "tgt": "en", "label": "Korean → English"},
    {"src": "ja", "tgt": "en", "label": "Japanese → English"},
    {"src": "zh", "tgt": "en", "label": "Chinese (Simplified) → English"},
    {"src": "zh-tw", "tgt": "en", "label": "Chinese (Traditional) → English"},
    {"src": "fr", "tgt": "en", "label": "French → English"},
    {"src": "de", "tgt": "en", "label": "German → English"},
    {"src": "es", "tgt": "en", "label": "Spanish → English"},
    {"src": "pt", "tgt": "en", "label": "Portuguese → English"},
    {"src": "ru", "tgt": "en", "label": "Russian → English"},
    {"src": "ar", "tgt": "en", "label": "Arabic → English"},
    {"src": "en", "tgt": "ko", "label": "English → Korean"},
    {"src": "en", "tgt": "ja", "label": "English → Japanese"},
]

LANGUAGE_LABELS: dict[str, str] = {
    "ko": "Korean", "ja": "Japanese", "zh": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "fr": "French", "de": "German",
    "es": "Spanish", "pt": "Portuguese", "ru": "Russian",
    "ar": "Arabic", "en": "English",
}
