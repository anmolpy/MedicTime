from __future__ import annotations

import logging
import os
import tempfile
import uuid
from starlette.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from .security import DemoGuard
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from .audio import transcribe_file, transcribe_segments
    from .config import settings
    from .kb import load_knowledge_base
    from .llm import generate_soap_note, receptionist_response
except ImportError:
    from audio import transcribe_file, transcribe_segments
    from config import settings
    from kb import load_knowledge_base
    from llm import generate_soap_note, receptionist_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("medictime-api")

CHUNK_SIZE = 1024 * 1024
ALLOWED_AUDIO_SUFFIXES = {".mp3", ".wav", ".webm", ".m4a", ".ogg", ".mp4", ".mpeg"}

app = FastAPI(
    title=settings.app_name,
    description="Backend API for MedicTime Cloudflare Pages + Render deployment",
    version="2.0.0",
)

app.add_middleware(DemoGuard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def internal_error(operation, exc):
    error_id = uuid.uuid4().hex
    # Exception messages and tracebacks may contain patient text or credentials.
    log.error("%s error_id=%s type=%s", operation, error_id, type(exc).__name__)
    return JSONResponse(status_code=500, content={
        "error": "Unable to process the request. Please try again.", "error_id": error_id})


# Serve only the reviewed frontend files, never the project directory or .env.
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(FRONTEND / "index.html")



def _validate_audio_upload(upload: UploadFile) -> None:
    suffix = Path(upload.filename or "upload.bin").suffix.lower()
    if suffix and suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported audio file type.")
    if upload.content_type and not upload.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be audio.")


async def save_upload(upload: UploadFile) -> str:
    _validate_audio_upload(upload)
    suffix = Path(upload.filename or "upload.bin").suffix or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    total_bytes = 0
    try:
        while True:
            chunk = await upload.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > settings.max_upload_mb * CHUNK_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Audio file is too large. Max size is {settings.max_upload_mb} MB.",
                )
            tmp.write(chunk)
        tmp.flush()
    except BaseException:
        tmp.close()
        os.unlink(tmp.name)
        raise
    finally:
        tmp.close()
        await upload.close()
    return tmp.name


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "whisper_model": settings.whisper_model,
        "knowledge_items": len(load_knowledge_base()),
        "tts_mode": "browser",
    }


@app.post("/api/agent-chat")
async def agent_chat(message: str = Form(..., min_length=1, max_length=4000)):
    try:
        response = await run_in_threadpool(receptionist_response, message)
        return {"response": response}
    except Exception as exc:
        return internal_error("agent_chat failed", exc)


@app.post("/api/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    tmp_path = None
    try:
        tmp_path = await save_upload(audio)
        transcription = await run_in_threadpool(transcribe_file, tmp_path)
        if not transcription:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not transcribe audio. Please try again."},
            )
        response = await run_in_threadpool(receptionist_response, transcription[:12000])
        return {
            "transcription": transcription,
            "response": response,
            "tts_mode": "browser",
        }
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    except Exception as exc:
        return internal_error("voice_chat failed", exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/soap-from-audio")
async def soap_from_audio(audio: UploadFile = File(...)):
    tmp_path = None
    try:
        tmp_path = await save_upload(audio)
        transcript = await run_in_threadpool(transcribe_segments, tmp_path)
        soap_note = await run_in_threadpool(generate_soap_note, transcript[:12000])
        return {"transcription": transcript, "soap": soap_note}
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    except Exception as exc:
        return internal_error("soap_from_audio failed", exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/{asset}", include_in_schema=False)
async def frontend_asset(asset: str):
    if asset not in {"style.css", "script.js", "config.js"}:
        raise HTTPException(status_code=404)
    return FileResponse(FRONTEND / asset)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
