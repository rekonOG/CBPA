from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Define default inventory dataset to serve as a demo out-of-the-box
DEFAULT_INVENTORY = [
    {"id": "SKU-1001", "itemName": "Wireless Mouse", "category": "Electronics", "quantity": 45, "price": 29.99, "supplier": "Logitech", "status": "In Stock"},
    {"id": "SKU-1002", "itemName": "Mechanical Keyboard", "category": "Electronics", "quantity": 8, "price": 89.99, "supplier": "Corsair", "status": "Low Stock"},
    {"id": "SKU-1003", "itemName": "USB-C Cable (1m)", "category": "Electronics", "quantity": 120, "price": 9.99, "supplier": "Anker", "status": "In Stock"},
    {"id": "SKU-1004", "itemName": "Bluetooth Speaker", "category": "Electronics", "quantity": 0, "price": 49.99, "supplier": "JBL", "status": "Out of Stock"},
    {"id": "SKU-2001", "itemName": "Ceramic Coffee Mug", "category": "Kitchenware", "quantity": 34, "price": 12.50, "supplier": "MugCo", "status": "In Stock"},
    {"id": "SKU-2002", "itemName": "Stainless Steel Water Bottle", "category": "Kitchenware", "quantity": 5, "price": 22.00, "supplier": "HydroFlask", "status": "Low Stock"},
    {"id": "SKU-3001", "itemName": "Ergonomic Office Chair", "category": "Furniture", "quantity": 12, "price": 189.00, "supplier": "Steelcase", "status": "In Stock"},
    {"id": "SKU-3002", "itemName": "Adjustable Standing Desk", "category": "Furniture", "quantity": 3, "price": 349.00, "supplier": "Fully", "status": "Low Stock"},
    {"id": "SKU-4001", "itemName": "Leather Journal", "category": "Stationery", "quantity": 50, "price": 15.00, "supplier": "Moleskine", "status": "In Stock"},
    {"id": "SKU-4002", "itemName": "Gel Pen Set (12-pack)", "category": "Stationery", "quantity": 80, "price": 8.50, "supplier": "Pilot", "status": "In Stock"},
]


class ItemCreate(BaseModel):
    id: str = Field(..., description="Unique serial code or SKU")
    itemName: str = Field(..., description="Name of the inventory item")
    category: str = Field("General", description="Product category")
    quantity: int = Field(0, ge=0, description="Quantity in stock")
    price: float = Field(0.0, ge=0.0, description="Unit price of the item")
    supplier: str = Field("Unknown", description="Supplier or manufacturer")


class ItemUpdate(BaseModel):
    itemName: str | None = None
    category: str | None = None
    quantity: int | None = None
    price: float | None = None
    supplier: str | None = None


def get_item_status(quantity: int) -> str:
    if quantity <= 0:
        return "Out of Stock"
    elif quantity <= 10:
        return "Low Stock"
    else:
        return "In Stock"


def _get_or_create_inventory_dataset(request: Request) -> dict[str, Any]:
    repository = request.app.state.dataset_repository
    if repository is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Please ensure datasets folder is writable.",
        )

    dataset = repository.get_dataset(dataset_type="inventory")
    if dataset is None:
        # Create a default dataset
        dataset = {
            "datasetId": str(uuid4()),
            "datasetType": "inventory",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "items": DEFAULT_INVENTORY.copy(),
        }
        repository.save_dataset(dataset)

    return dataset


@router.get("")
def get_inventory(request: Request) -> dict[str, Any]:
    dataset = _get_or_create_inventory_dataset(request)
    return {
        "datasetId": dataset.get("datasetId"),
        "items": dataset.get("items", []),
    }


@router.post("")
def add_item(request: Request, item: ItemCreate) -> dict[str, Any]:
    repository = request.app.state.dataset_repository
    dataset = _get_or_create_inventory_dataset(request)
    items = dataset.get("items", [])

    # Check if SKU / ID already exists
    if any(i["id"].strip().lower() == item.id.strip().lower() for i in items):
        raise HTTPException(
            status_code=400,
            detail=f"Item with Serial Code/SKU '{item.id}' already exists in inventory.",
        )

    new_item = item.dict()
    new_item["status"] = get_item_status(new_item["quantity"])
    items.append(new_item)

    dataset["items"] = items
    repository.save_dataset(dataset)

    return new_item


@router.put("/{item_id}")
def update_item(request: Request, item_id: str, payload: ItemUpdate) -> dict[str, Any]:
    repository = request.app.state.dataset_repository
    dataset = _get_or_create_inventory_dataset(request)
    items = dataset.get("items", [])

    target_item = None
    for item in items:
        if item["id"].strip().lower() == item_id.strip().lower():
            target_item = item
            break

    if not target_item:
        raise HTTPException(
            status_code=404,
            detail=f"Item with Serial Code/SKU '{item_id}' not found.",
        )

    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        target_item[key] = val

    if "quantity" in update_data:
        target_item["status"] = get_item_status(target_item["quantity"])

    dataset["items"] = items
    repository.save_dataset(dataset)

    return target_item


@router.delete("/{item_id}")
def delete_item(request: Request, item_id: str) -> dict[str, Any]:
    repository = request.app.state.dataset_repository
    dataset = _get_or_create_inventory_dataset(request)
    items = dataset.get("items", [])

    initial_len = len(items)
    items = [item for item in items if item["id"].strip().lower() != item_id.strip().lower()]

    if len(items) == initial_len:
        raise HTTPException(
            status_code=404,
            detail=f"Item with Serial Code/SKU '{item_id}' not found.",
        )

    dataset["items"] = items
    repository.save_dataset(dataset)

    return {"success": True, "message": f"Item '{item_id}' removed from inventory."}


@router.post("/upload")
async def upload_inventory(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    repository = request.app.state.dataset_repository
    if repository is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available.",
        )

    file_name = file.filename or ""
    extension = Path(file_name).suffix.lower()

    if extension not in {".csv", ".xls", ".xlsx"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only CSV and Excel sheets are allowed.",
        )

    file_bytes = await file.read()

    try:
        if extension == ".csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse CSV/Excel file: {str(e)}",
        )

    # Dynamic column mapping to robustly map incoming files
    col_mapping = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        if col_lower in {"id", "serial", "serialcode", "serial_code", "sku", "code"}:
            col_mapping[col] = "id"
        elif col_lower in {"itemname", "item_name", "name", "product", "title"}:
            col_mapping[col] = "itemName"
        elif col_lower in {"category", "type", "group"}:
            col_mapping[col] = "category"
        elif col_lower in {"quantity", "qty", "stock", "inventory", "count"}:
            col_mapping[col] = "quantity"
        elif col_lower in {"price", "cost", "rate", "unitprice", "unit_price"}:
            col_mapping[col] = "price"
        elif col_lower in {"supplier", "vendor", "manufacturer", "brand"}:
            col_mapping[col] = "supplier"

    # Rename matched columns
    df = df.rename(columns=col_mapping)

    # Ensure required columns or defaults
    if "id" not in df.columns:
        df["id"] = [f"SKU-{1000 + i}" for i in range(len(df))]
    if "itemName" not in df.columns:
        df["itemName"] = "Unnamed Item"
    if "category" not in df.columns:
        df["category"] = "General"
    if "quantity" not in df.columns:
        df["quantity"] = 0
    if "price" not in df.columns:
        df["price"] = 0.0
    if "supplier" not in df.columns:
        df["supplier"] = "Unknown"

    # Data cleaning
    df["id"] = df["id"].astype(str).str.strip()
    df["itemName"] = df["itemName"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0).astype(float)
    df["supplier"] = df["supplier"].astype(str).str.strip()

    # Calculate status
    df["status"] = df["quantity"].apply(get_item_status)

    # Drop any row without an ID
    df = df.dropna(subset=["id"])
    df = df[df["id"] != ""]

    # Keep only target columns and convert to records
    target_columns = ["id", "itemName", "category", "quantity", "price", "supplier", "status"]
    items_list = df[target_columns].to_dict(orient="records")

    dataset_id = str(uuid4())
    dataset = {
        "datasetId": dataset_id,
        "datasetType": "inventory",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "items": items_list,
    }

    repository.save_dataset(dataset)

    return {
        "success": True,
        "message": f"Successfully imported {len(items_list)} inventory items.",
        "datasetId": dataset_id,
        "items": items_list,
    }


@router.post("/sync")
def sync_inventory_datasets(request: Request) -> dict[str, Any]:
    repository = request.app.state.dataset_repository
    if repository is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available.",
        )

    # Get the latest product dataset
    product_dataset = repository.get_dataset(dataset_type="product")
    if not product_dataset:
        raise HTTPException(
            status_code=404,
            detail="No product dataset found to sync. Please upload a product dataset first.",
        )

    # Extract the cleaned file path
    product_data = product_dataset.get("productData", {})
    artifact_paths = product_data.get("artifactPaths", {})
    cleaned_file_path = artifact_paths.get("cleanedFilePath")

    if not cleaned_file_path or not Path(cleaned_file_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Product dataset artifact not found. Cannot sync.",
        )

    # Read the cleaned file
    try:
        if cleaned_file_path.endswith(".csv"):
            df = pd.read_csv(cleaned_file_path)
        else:
            df = pd.read_excel(cleaned_file_path)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to read product dataset: {str(e)}",
        )

    # Map columns heuristically just like upload
    col_mapping = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        if col_lower in {"id", "serial", "serialcode", "serial_code", "sku", "code", "product_id", "item_id"}:
            col_mapping[col] = "id"
        elif col_lower in {"itemname", "item_name", "name", "product", "title", "product_name"}:
            col_mapping[col] = "itemName"
        elif col_lower in {"category", "type", "group"}:
            col_mapping[col] = "category"
        elif col_lower in {"price", "cost", "rate", "unitprice", "unit_price"}:
            col_mapping[col] = "price"
        elif col_lower in {"supplier", "vendor", "manufacturer", "brand"}:
            col_mapping[col] = "supplier"

    df = df.rename(columns=col_mapping)

    # Handle missing columns
    if "id" not in df.columns:
        if "itemName" in df.columns:
            # generate id from itemName if possible
            df["id"] = "SYNC-" + df["itemName"].astype(str).str.upper().str.replace(r"[^A-Z0-9]+", "-", regex=True)
        else:
            df["id"] = [f"SYNC-{1000 + i}" for i in range(len(df))]

    if "itemName" not in df.columns:
        df["itemName"] = "Synced Product"
    if "category" not in df.columns:
        df["category"] = "General"
    if "price" not in df.columns:
        df["price"] = 0.0
    if "supplier" not in df.columns:
        df["supplier"] = "Unknown"

    # Data cleaning for syncing
    df["id"] = df["id"].astype(str).str.strip()
    df["itemName"] = df["itemName"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0).astype(float)
    df["supplier"] = df["supplier"].astype(str).str.strip()

    # We assume quantity is 0 initially for synced products if they don't have it
    if "quantity" not in df.columns:
        df["quantity"] = 0
    else:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)

    df = df.dropna(subset=["id"])
    df = df[df["id"] != ""]
    
    # Drop duplicates by ID
    df = df.drop_duplicates(subset=["id"], keep="first")

    target_columns = ["id", "itemName", "category", "quantity", "price", "supplier"]
    synced_items = df[target_columns].to_dict(orient="records")

    # Get current inventory
    inventory_dataset = _get_or_create_inventory_dataset(request)
    existing_items = inventory_dataset.get("items", [])
    
    # Map existing for quick lookup
    existing_map = {item["id"].strip().lower(): item for item in existing_items}
    
    added_count = 0
    updated_count = 0

    for item in synced_items:
        key = item["id"].strip().lower()
        if key in existing_map:
            # Update fields, but maybe preserve quantity
            existing_item = existing_map[key]
            existing_item["itemName"] = item["itemName"]
            existing_item["category"] = item["category"]
            existing_item["price"] = item["price"]
            existing_item["supplier"] = item["supplier"]
            # Recalculate status
            existing_item["status"] = get_item_status(existing_item.get("quantity", 0))
            updated_count += 1
        else:
            # Add new item
            item["status"] = get_item_status(item["quantity"])
            existing_items.append(item)
            added_count += 1

    inventory_dataset["items"] = existing_items
    repository.save_dataset(inventory_dataset)

    return {
        "success": True,
        "message": f"Sync complete. Added {added_count} items and updated {updated_count} existing items.",
        "added": added_count,
        "updated": updated_count
    }
