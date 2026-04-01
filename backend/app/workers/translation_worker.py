"""GPU translation worker — runs on RunPod Serverless / Modal.

Handles NLLB-200 inference for Korean→English translation.
"""
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Loaded once at cold start
_model = None
_tokenizer = None

MODEL_ID = "facebook/nllb-200-distilled-600M"
SRC_LANG = "kor_Hang"
TGT_LANG = "eng_Latn"


def _load_model():
    global _model, _tokenizer
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
        _model.eval()
    return _model, _tokenizer


def handler(job: dict) -> dict:
    """RunPod serverless handler.

    Input:
        job["input"]["texts"]: list of Korean strings
        job["input"]["src_lang"]: source language code (default: kor_Hang)
        job["input"]["tgt_lang"]: target language code (default: eng_Latn)

    Output:
        {"translations": [str, ...]}
    """
    input_data = job.get("input", {})
    texts = input_data["texts"]
    src_lang = input_data.get("src_lang", SRC_LANG)
    tgt_lang = input_data.get("tgt_lang", TGT_LANG)

    model, tokenizer = _load_model()

    tokenizer.src_lang = src_lang
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)

    tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang)
    outputs = model.generate(**inputs, forced_bos_token_id=tgt_lang_id, max_new_tokens=256)

    translations = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return {"translations": translations}


if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
