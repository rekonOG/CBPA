from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    mongodb_uri: str
    mongodb_db_name: str
    mongodb_collection: str
    cors_origins: list[str]
    models_dir: Path
    model_version: str
    preprocessing_output_dir: Path


BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BASE_DIR / "models"
PREPROCESSING_OUTPUT_DIR = BASE_DIR / "preprocessing_outputs"


def _parse_cors_origins(raw_value: str) -> list[str]:
    origins = [item.strip() for item in raw_value.split(",") if item.strip()]
    return origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


settings = Settings(
    app_name=os.getenv("APP_NAME", "Customer Buying Pattern Analysis API"),
    mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
    mongodb_db_name=os.getenv("MONGODB_DB_NAME", "cbpa"),
    mongodb_collection=os.getenv("MONGODB_COLLECTION", "datasets"),
    cors_origins=_parse_cors_origins(
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        )
    ),
    models_dir=MODELS_DIR,
    model_version=os.getenv("MODEL_VERSION", "v1"),
    preprocessing_output_dir=Path(
        os.getenv("PREPROCESSING_OUTPUT_DIR", str(PREPROCESSING_OUTPUT_DIR))
    ),
)
