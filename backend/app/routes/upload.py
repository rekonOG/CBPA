from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ..config import settings
from ..services.data_preprocessing import InputPreprocessor
from ..services.inference import run_segmentation
from ..services.insights import (
    build_analysis_payload,
    build_dashboard_payload,
    build_insights_payload,
    build_preview_payload,
    build_results_payload,
)
from ..services.pipeline_config import EncodingStrategy, PipelineConfig, ScalingMethod
from ..services.preprocess import (
    SUPPORTED_EXTENSIONS,
    build_customer_frame,
    to_serializable_records,
)
from ..services.universal_preprocessing import UniversalPreprocessor

router = APIRouter(tags=["upload"])


def _parse_scaling_method(raw_value: str) -> ScalingMethod:
    normalized = (raw_value or "").strip().lower()
    for method in ScalingMethod:
        if method.value == normalized:
            return method

    supported_methods = ", ".join(method.value for method in ScalingMethod)
    raise HTTPException(
        status_code=400,
        detail=f"Invalid scaling_method. Supported values: {supported_methods}.",
    )


@router.post("/upload")
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> dict:
    print("[UPLOAD] upload_dataset started")
    file_name = file.filename or ""
    extension = Path(file_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only CSV, XLS, and XLSX files are supported.")

    file_bytes = await file.read()
    print(f"[UPLOAD] received file {file_name}, size={len(file_bytes)} bytes")

    try:
        input_preprocessor = InputPreprocessor()
        raw_frame, engineered_frame, engineered_input_array = input_preprocessor.load_uploaded_file(
            file_name,
            file_bytes,
        )
        print(f"[UPLOAD] parsed frame shape {raw_frame.shape} engineered shape {engineered_frame.shape}")
        customers, quality = build_customer_frame(raw_frame)
        print(f"[UPLOAD] built customer frame shape {customers.shape}")
    except ValueError as exc:
        print(f"[UPLOAD] validation error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request.app.state.last_uploaded_input_array = engineered_input_array
    request.app.state.last_uploaded_feature_frame = engineered_frame

    inference_artifacts = request.app.state.inference_artifacts
    inference_result = run_segmentation(
        customers,
        inference_artifacts,
        feature_frame=engineered_frame,
    )

    dataset_id = str(uuid4())
    upload_meta = {
        "fileName": file_name,
        "size": file.size if file.size is not None else len(file_bytes),
        "type": file.content_type or "application/octet-stream",
        "uploadedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    preview_payload = build_preview_payload(inference_result.customers, quality, upload_meta)
    dashboard_payload = build_dashboard_payload(
        inference_result.customers,
        upload_meta,
        quality,
        inference_result.segment_mix,
        inference_result.model_meta,
    )
    analysis_payload = build_analysis_payload(
        inference_result.customers,
        inference_result.cluster_distribution,
        inference_result.cluster_profiles,
        inference_result.silhouette_score,
        inference_result.elbow_method,
        inference_result.model_meta,
    )
    results_payload = build_results_payload(
        inference_result.customers,
        inference_result.segment_mix,
        inference_result.model_meta,
    )
    insights_payload = build_insights_payload(
        inference_result.customers,
        quality,
        inference_result.model_meta,
    )

    dataset_document = {
        "datasetId": dataset_id,
        "datasetType": "customer",
        "createdAt": datetime.now(timezone.utc),
        "uploadMeta": upload_meta,
        "quality": quality,
        "preview": preview_payload,
        "dashboard": dashboard_payload,
        "analysis": analysis_payload,
        "results": results_payload,
        "insights": insights_payload,
        "modelMeta": inference_result.model_meta,
    }

    repository = request.app.state.dataset_repository
    if repository is not None:
        repository.save_dataset(dataset_document)

    print(f"[UPLOAD] upload successful datasetId={dataset_id}")
    return {
        "success": True,
        "message": "Dataset uploaded and queued for analysis.",
        "datasetId": dataset_id,
        "uploadMeta": upload_meta,
        "preview": {
            "rows": quality["totalRows"],
            "columns": quality["totalColumns"],
        },
        "modelMeta": inference_result.model_meta,
    }


@router.post("/upload-product")
async def upload_product_dataset(
    request: Request,
    file: UploadFile = File(...),
    scaling_method: str = Form("standard"),
    use_binary_label_encoding: bool = Form(True),
) -> dict:
    file_name = file.filename or ""
    extension = Path(file_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only CSV, XLS, and XLSX files are supported.")

    file_bytes = await file.read()
    dataset_id = str(uuid4())

    try:
        pipeline_config = PipelineConfig(
            scaling_method=_parse_scaling_method(scaling_method),
            encoding_strategy=EncodingStrategy.ONE_HOT,
            binary_encoding_strategy=(
                EncodingStrategy.LABEL if use_binary_label_encoding else None
            ),
            handle_duplicates=True,
            handle_missing_values=True,
            engineer_features=True,
            datetime_feature_extraction=True,
        )
        preprocessor = UniversalPreprocessor(config=pipeline_config)
        preprocessing_result = preprocessor.preprocess_uploaded_file(
            file_name=file_name,
            file_bytes=file_bytes,
            output_dir=settings.preprocessing_output_dir,
            dataset_name=f"{Path(file_name).stem}_{dataset_id[:8]}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive API error handling
        raise HTTPException(
            status_code=500,
            detail="Failed to preprocess uploaded dataset. Please verify file contents and retry.",
        ) from exc

    upload_meta = {
        "fileName": file_name,
        "size": file.size if file.size is not None else len(file_bytes),
        "type": file.content_type or "application/octet-stream",
        "uploadedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    dataset_document = {
        "datasetId": dataset_id,
        "datasetType": "product",
        "createdAt": datetime.now(timezone.utc),
        "uploadMeta": upload_meta,
        "productData": {
            "rows": int(preprocessing_result.report.original_shape[0]),
            "columns": int(preprocessing_result.report.original_shape[1]),
            "columnNames": [str(column) for column in preprocessing_result.cleaned_frame.columns],
            "processedColumnNames": [
                str(column) for column in preprocessing_result.processed_frame.columns
            ],
            "cleanedPreviewRecords": to_serializable_records(
                preprocessing_result.cleaned_frame.head(50)
            ),
            "processedPreviewRecords": to_serializable_records(
                preprocessing_result.processed_frame.head(50)
            ),
            "preprocessingReport": preprocessing_result.report.to_dict(),
            "artifactPaths": {
                "cleanedFilePath": str(preprocessing_result.cleaned_file_path),
                "processedFilePath": str(preprocessing_result.processed_file_path),
                "pipelineFilePath": str(preprocessing_result.pipeline_file_path),
                "reportFilePath": str(preprocessing_result.report_file_path),
            },
        },
    }

    repository = request.app.state.dataset_repository
    if repository is not None:
        repository.save_dataset(dataset_document)

    return {
        "success": True,
        "message": "Product dataset uploaded, preprocessed, and stored successfully.",
        "datasetId": dataset_id,
        "uploadMeta": upload_meta,
        "preview": {
            "rows": int(preprocessing_result.processed_frame.shape[0]),
            "columns": int(preprocessing_result.processed_frame.shape[1]),
        },
        "preprocessingSummary": {
            "duplicatesRemoved": preprocessing_result.report.duplicate_rows_removed,
            "missingValuesHandled": preprocessing_result.report.missing_values_filled_count,
            "encodedColumns": sorted(preprocessing_result.report.encoded_columns.keys()),
            "scaledColumns": preprocessing_result.report.scaled_columns,
            "engineeredFeatures": preprocessing_result.report.engineered_features,
            "scalingMethod": preprocessing_result.report.scaling_method,
        },
        "artifactPaths": {
            "cleanedFilePath": str(preprocessing_result.cleaned_file_path),
            "processedFilePath": str(preprocessing_result.processed_file_path),
            "pipelineFilePath": str(preprocessing_result.pipeline_file_path),
            "reportFilePath": str(preprocessing_result.report_file_path),
        },
    }
