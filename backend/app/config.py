from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "MedicTime API")
    clinic_name: str = os.getenv("CLINIC_NAME", "MedicTime Clinic")
    hf_token: str | None = os.getenv("HF_TOKEN")
    hf_model: str = os.getenv("HF_MODEL", "meta-llama/Llama-3.2-1B-Instruct")
    whisper_model: str = os.getenv("WHISPER_MODEL", "tiny")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "15"))
    allowed_origins: list[str] | None = None


settings = Settings(
    allowed_origins=_split_csv(
        os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "http://localhost:3000,"
            "http://127.0.0.1:3000,"
            "http://localhost:5500,"
            "http://127.0.0.1:5500",
        )
    )
)
