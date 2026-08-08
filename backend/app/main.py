from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import initialize_repository
from .routes.analytics import router as analytics_router
from .routes.upload import router as upload_router
from .routes.inventory import router as inventory_router
from .services.inference import load_inference_artifacts

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    settings.preprocessing_output_dir.mkdir(parents=True, exist_ok=True)
    try:
        repository = initialize_repository(settings)
        app.state.dataset_repository = repository
    except Exception as e:
        print(f"Failed to initialize SQLite database: {e}")
        app.state.dataset_repository = None
    app.state.inference_artifacts = load_inference_artifacts(
        settings.models_dir,
        settings.model_version,
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    pass  # SQLite connections are closed after each query; nothing to clean up here.


app.include_router(upload_router)
app.include_router(analytics_router)
app.include_router(inventory_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
