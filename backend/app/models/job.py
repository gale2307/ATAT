from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    queued = "queued"
    downloading = "downloading"
    transcribing = "transcribing"
    translating = "translating"
    rendering = "rendering"
    done = "done"
    error = "error"


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True, unique=True)
    url: str
    stt_model: str
    translation_engine: str
    domain: str = "general"
    src_lang: str = "ko"
    tgt_lang: str = "en"
    download_mode: str = "audio_only"  # "audio_only" | "video"
    status: JobStatus = JobStatus.queued
    progress: int = 0
    output_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
