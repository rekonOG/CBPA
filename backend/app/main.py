from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import initialize_repository
from .routes.analytics import router as analytics_router
from .routes.upload import router as upload_router
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
        mongo_client, repository = initialize_repository(settings)
        app.state.mongo_client = mongo_client
        app.state.dataset_repository = repository
    except Exception as e:
        print(f"MongoDB not available: {e}. Running without database.")
        app.state.mongo_client = None
        app.state.dataset_repository = None
    app.state.inference_artifacts = load_inference_artifacts(
        settings.models_dir,
        settings.model_version,
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    mongo_client = getattr(app.state, "mongo_client", None)
    if mongo_client is not None:
        mongo_client.close()


app.include_router(upload_router)
app.include_router(analytics_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
