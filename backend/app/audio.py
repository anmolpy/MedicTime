from __future__ import annotations

import subprocess
from functools import lru_cache

import imageio_ffmpeg
import numpy as np
import whisper

try:
    from .config import settings
except ImportError:
    from config import settings


def decode_audio(file_path: str, sample_rate: int = 16000) -> np.ndarray:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-threads",
        "0",
        "-i",
        file_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    audio = np.frombuffer(result.stdout, dtype=np.int16).flatten()
    return audio.astype(np.float32) / 32768.0


@lru_cache(maxsize=1)
def get_whisper_model():
    return whisper.load_model(settings.whisper_model)


def transcribe_file(file_path: str) -> str:
    audio_np = decode_audio(file_path)
    result = get_whisper_model().transcribe(audio_np, fp16=False)
    return result.get("text", "").strip()


def transcribe_segments(file_path: str) -> str:
    audio_np = decode_audio(file_path)
    result = get_whisper_model().transcribe(audio_np, fp16=False)
    transcript_lines = []
    for segment in result.get("segments", []):
        text = segment.get("text", "").strip()
        if text:
            transcript_lines.append(f"[{segment['start']:.1f}s] {text}")
    if transcript_lines:
        return "\n".join(transcript_lines)
    return result.get("text", "").strip()
