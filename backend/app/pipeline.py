"""End-to-end job processing pipeline."""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from sqlmodel import Session, select

from app.config import settings
from app.models.database import engine
from app.models.job import Job, JobStatus
from app.services.downloader import download_video, extract_audio
from app.services.subtitle import generate_srt, generate_vtt
from app.services.transcriber import transcribe, transcribe_gpt4o, transcribe_mock
from app.services.translator import get_translation_engine
from app.socket import emit_done, emit_error, emit_progress


async def run_job(job_id: str):
    """Orchestrate the full transcription + translation pipeline for a job."""
    loop = asyncio.get_running_loop()

    def _update(status: JobStatus, progress: int, **kwargs):
        with Session(engine) as s:
            job = s.exec(select(Job).where(Job.job_id == job_id)).first()
            if not job:
                return
            job.status = status
            job.progress = progress
            for k, v in kwargs.items():
                setattr(job, k, v)
            s.add(job)
            s.commit()

    def _get_job() -> Job | None:
        with Session(engine) as s:
            return s.exec(select(Job).where(Job.job_id == job_id)).first()

    try:
        job = _get_job()
        if not job:
            return

        output_dir = Path(settings.storage_path) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: Download video ---
        _update(JobStatus.downloading, 5)
        await emit_progress(job_id, 5, "downloading")
        logger.info("[%s] Downloading video: %s", job_id, job.url)

        video_path, _title = await loop.run_in_executor(None, download_video, job.url, job_id)
        logger.info("[%s] Download complete: %s", job_id, video_path)

        # Extract audio from video for STT
        audio_path = output_dir / "audio.wav"
        logger.info("[%s] Extracting audio", job_id)
        await loop.run_in_executor(None, extract_audio, video_path, audio_path)
        logger.info("[%s] Audio extracted: %s", job_id, audio_path)

        # --- Step 2: Transcribe ---
        _update(JobStatus.transcribing, 30)
        await emit_progress(job_id, 30, "transcribing")
        logger.info("[%s] Transcribing with model: %s", job_id, job.stt_model)

        if settings.mock_mode:
            segments = await loop.run_in_executor(None, transcribe_mock)
        elif job.stt_model == "gpt-4o-transcribe":
            segments = await loop.run_in_executor(None, transcribe_gpt4o, audio_path, job.src_lang)
        else:
            segments = await loop.run_in_executor(None, transcribe, audio_path, job.stt_model, job.src_lang)
        logger.info("[%s] Transcription complete: %d segments", job_id, len(segments))

        # --- Step 3: Translate ---
        _update(JobStatus.translating, 60)
        await emit_progress(job_id, 60, "translating")
        logger.info("[%s] Translating with engine: %s", job_id, job.translation_engine)

        engine_inst = get_translation_engine(
            job.translation_engine,
            domain=job.domain,
            src_lang=job.src_lang,
            tgt_lang=job.tgt_lang,
            mock=settings.mock_mode,
        )
        translated = await loop.run_in_executor(None, engine_inst.translate, segments)
        logger.info("[%s] Translation complete: %d segments", job_id, len(translated))

        # --- Step 4: Generate subtitles ---
        _update(JobStatus.rendering, 80)
        await emit_progress(job_id, 80, "rendering")
        logger.info("[%s] Generating subtitle files", job_id)

        generate_srt(translated, output_dir / "subtitles.srt")
        generate_vtt(translated, output_dir / "subtitles.vtt")

        _update(
            JobStatus.done, 100,
            output_path=str(video_path),
            subtitle_path=str(output_dir / "subtitles.srt"),
        )
        logger.info("[%s] Job complete", job_id)
        await emit_done(
            job_id,
            output_url=f"/files/{job_id}/video.mp4",
            subtitle_url=f"/files/{job_id}/subtitles.vtt",
            srt_url=f"/files/{job_id}/subtitles.srt",
        )

    except Exception as exc:
        logger.exception("[%s] Job failed: %s", job_id, exc)
        _update(JobStatus.error, 0, error=str(exc))
        await emit_error(job_id, str(exc))
        raise
