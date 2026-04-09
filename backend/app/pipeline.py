"""End-to-end job processing pipeline."""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from sqlmodel import Session, select

from app.config import settings
from app.models.database import engine
from app.models.job import Job, JobStatus
from app.services.downloader import download_audio, download_video, extract_audio
from app.services.subtitle import generate_srt, generate_vtt
from app.services.transcriber import get_transcription_engine
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

        logger.info("[%s] Job started — model=%s engine=%s domain=%s %s→%s mode=%s",
                    job_id, job.stt_model, job.translation_engine,
                    job.domain, job.src_lang, job.tgt_lang, job.download_mode)

        output_dir = Path(settings.storage_path) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: Download ---
        _update(JobStatus.downloading, 5)
        await emit_progress(job_id, 5, "downloading")

        audio_path = output_dir / "audio.wav"

        if job.download_mode == "audio_only":
            logger.info("[%s] Downloading audio: %s", job_id, job.url)
            audio_path, _title = await loop.run_in_executor(None, download_audio, job.url, job_id)
            video_path = None
        else:
            logger.info("[%s] Downloading video: %s", job_id, job.url)
            video_path, _title = await loop.run_in_executor(None, download_video, job.url, job_id)
            logger.info("[%s] Extracting audio", job_id)
            await loop.run_in_executor(None, extract_audio, video_path, audio_path)

        logger.info("[%s] Download complete", job_id)

        # --- Step 2: Transcribe ---
        _update(JobStatus.transcribing, 30)
        await emit_progress(job_id, 30, "transcribing")
        logger.info("[%s] Transcription started — model=%s", job_id, job.stt_model)

        transcriber = get_transcription_engine(job.stt_model, mock=settings.mock_mode)
        segments = await loop.run_in_executor(None, transcriber.transcribe, audio_path, job.src_lang)
        logger.info("[%s] Transcription finished — %d segments", job_id, len(segments))

        # --- Step 3: Translate ---
        _update(JobStatus.translating, 60)
        await emit_progress(job_id, 60, "translating")
        logger.info("[%s] Translation started — engine=%s", job_id, job.translation_engine)

        translator = get_translation_engine(
            job.translation_engine,
            domain=job.domain,
            src_lang=job.src_lang,
            tgt_lang=job.tgt_lang,
            mock=settings.mock_mode,
        )
        translated = await loop.run_in_executor(None, translator.translate, segments)
        logger.info("[%s] Translation finished — %d segments", job_id, len(translated))

        # --- Step 4: Generate subtitles ---
        _update(JobStatus.rendering, 80)
        await emit_progress(job_id, 80, "rendering")

        generate_srt(translated, output_dir / "subtitles.srt")
        if job.download_mode == "video":
            generate_vtt(translated, output_dir / "subtitles.vtt")

        _update(
            JobStatus.done, 100,
            output_path=str(video_path) if video_path else None,
            subtitle_path=str(output_dir / "subtitles.srt"),
        )
        logger.info("[%s] Job done", job_id)

        if job.download_mode == "audio_only":
            await emit_done(
                job_id,
                srt_url=f"/files/{job_id}/subtitles.srt",
                embed_url=job.url,
            )
        else:
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
