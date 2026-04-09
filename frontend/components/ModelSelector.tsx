"use client";

import type { ModelConfig } from "@/app/page";

const STT_MODELS = [
  { value: "whisper-large-v3", label: "Whisper large-v3" },
  { value: "whisper-large-v3-turbo", label: "Whisper large-v3-turbo" },
  { value: "whisper-medium", label: "Whisper medium" },
  { value: "whisper-large-v3-lol", label: "Whisper large-v3 (LoL fine-tuned)" },
  { value: "gpt-4o-transcribe", label: "GPT-4o Transcribe (API)" },
];

const TRANSLATION_ENGINES = [
  { value: "qwen-mt", label: "Qwen-MT Turbo (API)" },
  { value: "nllb-600m", label: "NLLB-200 600M (self-hosted)" },
  { value: "nllb-3.3b", label: "NLLB-200 3.3B (self-hosted)" },
  { value: "gpt-4o", label: "GPT-4o (premium)" },
];

const DOMAINS = [
  { value: "general", label: "General" },
  { value: "lol-esports", label: "LoL Esports" },
  { value: "erbs-general", label: "Eternal Return" },
  { value: "kpop", label: "K-Pop" },
  { value: "kdrama", label: "K-Drama" },
  { value: "anime", label: "Anime" },
  { value: "tech", label: "Tech / Dev" },
];

const LANGUAGE_PAIRS = [
  { src: "ko", tgt: "en", label: "Korean → English" },
  { src: "ja", tgt: "en", label: "Japanese → English" },
  { src: "zh", tgt: "en", label: "Chinese (Simplified) → English" },
  { src: "zh-tw", tgt: "en", label: "Chinese (Traditional) → English" },
  { src: "fr", tgt: "en", label: "French → English" },
  { src: "de", tgt: "en", label: "German → English" },
  { src: "es", tgt: "en", label: "Spanish → English" },
  { src: "pt", tgt: "en", label: "Portuguese → English" },
  { src: "ru", tgt: "en", label: "Russian → English" },
  { src: "ar", tgt: "en", label: "Arabic → English" },
  { src: "en", tgt: "ko", label: "English → Korean" },
  { src: "en", tgt: "ja", label: "English → Japanese" },
];

type Props = {
  config: ModelConfig;
  onChange: (config: ModelConfig) => void;
};

export default function ModelSelector({ config, onChange }: Props) {
  const selectedPair = LANGUAGE_PAIRS.find(
    (p) => p.src === config.srcLang && p.tgt === config.tgtLang
  );

  function handleLangPairChange(value: string) {
    const [src, tgt] = value.split("|");
    onChange({ ...config, srcLang: src, tgtLang: tgt });
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      <div>
        <label className="block text-xs text-gray-400 mb-1">Language</label>
        <select
          value={`${config.srcLang}|${config.tgtLang}`}
          onChange={(e) => handleLangPairChange(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          {LANGUAGE_PAIRS.map((p) => (
            <option key={`${p.src}|${p.tgt}`} value={`${p.src}|${p.tgt}`}>{p.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">Domain</label>
        <select
          value={config.domain}
          onChange={(e) => onChange({ ...config, domain: e.target.value })}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          {DOMAINS.map((d) => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">STT Model</label>
        <select
          value={config.sttModel}
          onChange={(e) => onChange({ ...config, sttModel: e.target.value })}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          {STT_MODELS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">Translation</label>
        <select
          value={config.translationEngine}
          onChange={(e) => onChange({ ...config, translationEngine: e.target.value })}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          {TRANSLATION_ENGINES.map((e) => (
            <option key={e.value} value={e.value}>{e.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">Mode</label>
        <select
          value={config.downloadMode}
          onChange={(e) => onChange({ ...config, downloadMode: e.target.value })}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          <option value="audio_only">Audio only</option>
          <option value="video">Download video</option>
        </select>
      </div>
    </div>
  );
}
