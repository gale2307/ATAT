from fastapi import APIRouter
from app.config import LANGUAGE_PAIRS, STT_MODELS, TRANSLATION_ENGINES

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def list_models():
    return {"sttModels": STT_MODELS, "translationEngines": TRANSLATION_ENGINES, "languagePairs": LANGUAGE_PAIRS}
