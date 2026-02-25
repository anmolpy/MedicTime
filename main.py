"""
MedicTime FastAPI Server
Wraps load_llama.py and rag_system.py into a REST API
"""

import os
import sys
import logging
import tempfile
import traceback
import base64
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# ── Logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("medictime")

# ── Lazy imports from existing modules ────────────────────────
# We import at module level so startup failures are visible immediately.
# Both modules run their own load_dotenv() so env vars are populated.

log.info("Loading load_llama module …")
from Load_llama import (
    receptionist_response,
    whisper_model,
    embedder,
    collection,
    eleven_client,
    transcribe_audio,
)
from elevenlabs import VoiceSettings
log.info("load_llama module loaded ✅")

log.info("Loading rag_system module …")
import rag_system  # We'll call a patched version of process_clinical_audio below
import whisper as _whisper

# ── Decode audio using imageio-ffmpeg (no system ffmpeg needed) ──
import imageio_ffmpeg as _iio_ffmpeg
import subprocess as _subprocess
import numpy as _np

_ffmpeg_exe = _iio_ffmpeg.get_ffmpeg_exe()
log.info(f"ffmpeg binary: {_ffmpeg_exe}")

def _decode_audio(file_path: str, sample_rate: int = 16000) -> _np.ndarray:
    """Decode any audio file to float32 numpy array using imageio-ffmpeg."""
    cmd = [
        _ffmpeg_exe, "-nostdin", "-threads", "0",
        "-i", file_path,
        "-f", "s16le", "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-"
    ]
    result = _subprocess.run(cmd, capture_output=True, check=True)
    audio = _np.frombuffer(result.stdout, dtype=_np.int16).flatten()
    return audio.astype(_np.float32) / 32768.0
log.info("rag_system module loaded ✅")

# ── Patch process_clinical_audio to return a dict ─────────────
def process_clinical_audio_api(audio_path: str) -> dict:
    """
    Adapted version of rag_system.process_clinical_audio that returns a dict
    instead of writing a file.  Reuses the already-loaded whisper_model from
    Load_llama to avoid double-loading, and converts webm->wav if needed.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info(f"[SOAP] Transcribing on {device.upper()} …")

    # Decode audio to numpy array via imageio-ffmpeg, then transcribe
    audio_np = _decode_audio(audio_path)
    result = whisper_model.transcribe(audio_np, fp16=False)

    transcript_lines = []
    for segment in result["segments"]:
        text = segment.get("text", "").strip()
        if text:
            transcript_lines.append(f"[{segment['start']:.1f}s] {text}")
    full_transcript = "\n".join(transcript_lines)
    log.info("[SOAP] Transcription complete.")

    user_prompt = f"""
You are an expert clinical medical scribe. Your ONLY job is to read the provided transcript and extract a professional SOAP note.

CRITICAL RULES:
1. First, deduce which speaker is the Doctor and which is the Patient based on the context.
2. DO NOT write dialogue or continue the conversation.
3. Return ONLY the Subjective, Objective, Assessment, and Plan sections.
4. Be concise and use medical terminology where appropriate. If a section is empty, write "None reported".

TRANSCRIPT:
{full_transcript}

FORMAT:
SUBJECTIVE:
- 
OBJECTIVE:
- 
ASSESSMENT:
- 
PLAN:
- 
"""

    log.info("[SOAP] Calling HuggingFace for SOAP note …")
    llm_response = rag_system.hf_client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert clinical medical scribe. Extract professional SOAP notes from medical conversation transcripts.",
            },
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=800,
        temperature=0.1,
    )
    soap_note = llm_response.choices[0].message.content.strip()
    log.info("[SOAP] SOAP note generated.")

    return {"transcription": full_transcript, "soap": soap_note}


# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(
    title="MedicTime API",
    description="Medical receptionist voice agent + clinical SOAP note generator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper: save upload to temp file ──────────────────────────
async def save_upload(upload: UploadFile, suffix: str = ".mp3") -> str:
    """Saves an UploadFile to a temporary file and returns its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        contents = await upload.read()
        tmp.write(contents)
        tmp.flush()
    finally:
        tmp.close()
    return tmp.name


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    """Serve the frontend - place index.html in the same folder as main.py"""
    html_path = Path(__file__).parent / "index.html"
    if not html_path.exists():
        return {"error": "index.html not found. Place it in the same directory as main.py"}
    return FileResponse(html_path)

@app.get("/health")
async def health():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return {
        "status": "ok",
        "device": device,
        "rag_documents": collection.count(),
    }


@app.post("/api/soap-from-audio")
async def soap_from_audio(audio: UploadFile = File(...)):
    """
    Upload an audio file of a doctor–patient conversation.
    Returns a JSON with 'transcription' and 'soap' fields.
    """
    suffix = Path(audio.filename).suffix or ".mp3"
    tmp_path = await save_upload(audio, suffix=suffix)
    try:
        log.info(f"[/api/soap-from-audio] Processing {audio.filename} …")
        result = process_clinical_audio_api(tmp_path)
        return JSONResponse(content=result)
    except Exception as exc:
        tb = traceback.format_exc()
        log.error(f"[/api/soap-from-audio] Error: {exc}\n{tb}")
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "details": tb},
        )
    finally:
        os.unlink(tmp_path)


@app.post("/api/agent-chat")
async def agent_chat(message: str = Form(...)):
    """
    Send a text message to the RAG-enhanced receptionist.
    Returns {"response": "..."}.
    """
    try:
        log.info(f"[/api/agent-chat] message={message[:80]!r} …")
        response = receptionist_response(message)
        return JSONResponse(content={"response": response})
    except Exception as exc:
        log.error(f"[/api/agent-chat] Error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "details": traceback.format_exc()},
        )


@app.post("/api/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    """
    Upload a voice recording.
    1. Transcribe with Whisper.
    2. Get RAG receptionist response.
    3. Convert response to speech via ElevenLabs.
    Returns {"transcription": "...", "response": "...", "audio_b64": "..."}.
    """
    suffix = Path(audio.filename).suffix or ".webm"
    tmp_path = await save_upload(audio, suffix=suffix)
    try:
        log.info(f"[/api/voice-chat] Transcribing {audio.filename} …")
        # Decode audio to numpy array via imageio-ffmpeg, then transcribe
        audio_np = _decode_audio(tmp_path)
        result = whisper_model.transcribe(audio_np, fp16=False)
        transcription = result["text"].strip()
        log.info(f"[/api/voice-chat] Raw transcription: {transcription!r}")

        if not transcription:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not transcribe audio. Please try again."},
            )

        log.info(f"[/api/voice-chat] Transcription: {transcription[:80]!r}")
        response_text = receptionist_response(transcription)
        log.info(f"[/api/voice-chat] Response: {response_text[:80]!r}")

        # ElevenLabs TTS
        audio_stream = eleven_client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            text=response_text,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True,
            ),
        )
        audio_bytes = b"".join(audio_stream)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse(
            content={
                "transcription": transcription,
                "response": response_text,
                "audio_b64": audio_b64,
            }
        )
    except Exception as exc:
        log.error(f"[/api/voice-chat] Error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "details": traceback.format_exc()},
        )
    finally:
        os.unlink(tmp_path)


# ── Startup event ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("=" * 60)
    log.info("🏥  MedicTime API Server starting …")
    log.info(f"   Device      : {device.upper()}")
    log.info(f"   Whisper     : base model loaded ✅")
    log.info(f"   Embedder    : all-MiniLM-L6-v2 loaded ✅")
    log.info(f"   RAG docs    : {collection.count()} documents")
    log.info(f"   LLM         : meta-llama/Meta-Llama-3-8B-Instruct (HF API)")
    log.info(f"   TTS         : ElevenLabs (Rachel voice)")
    log.info("   Endpoints   :")
    log.info("     POST /api/soap-from-audio")
    log.info("     POST /api/agent-chat")
    log.info("     POST /api/voice-chat")
    log.info(f"   Server URL  : http://localhost:8001")
    log.info("=" * 60)


# ── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
