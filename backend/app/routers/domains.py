from fastapi import APIRouter
from app.config import DOMAINS, LANGUAGE_PAIRS

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("")
async def list_domains():
    return {"domains": DOMAINS, "languagePairs": LANGUAGE_PAIRS}
