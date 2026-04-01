const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type ModelConfig = {
  sttModel: string;
  translationEngine: string;
  domain: string;
  srcLang: string;
  tgtLang: string;
};

export async function submitJob(url: string, models: ModelConfig): Promise<{ jobId: string }> {
  const res = await fetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      stt_model: models.sttModel,
      translation_engine: models.translationEngine,
      domain: models.domain,
      src_lang: models.srcLang,
      tgt_lang: models.tgtLang,
    }),
  });
  if (!res.ok) throw new Error(`Failed to submit job: ${res.statusText}`);
  return res.json();
}

export async function getJob(jobId: string) {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.statusText}`);
  return res.json();
}

export async function getModels() {
  const res = await fetch(`${BASE}/models`);
  if (!res.ok) throw new Error(`Failed to fetch models: ${res.statusText}`);
  return res.json();
}

export async function getDomains() {
  const res = await fetch(`${BASE}/domains`);
  if (!res.ok) throw new Error(`Failed to fetch domains: ${res.statusText}`);
  return res.json();
}
