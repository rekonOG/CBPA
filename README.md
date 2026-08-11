# Customer Buying Pattern Analysis

This project includes:

- React frontend (`src/`)
- FastAPI backend with SQLite storage (`backend/`)

## API Contract

The frontend expects and consumes these endpoints:

- `POST /upload`
- `POST /upload-product`
- `GET /preview?datasetId=...`
- `GET /dashboard?datasetId=...`
- `GET /analyze?datasetId=...`
- `GET /results?datasetId=...`
- `GET /insights?datasetId=...`
- `GET /product-analysis?datasetId=...&forecastPeriods=12&frequency=auto`
- `GET /inventory`
- `POST /inventory`
- `PUT /inventory/{id}`
- `DELETE /inventory/{id}`
- `POST /inventory/sync`

## Backend Setup (FastAPI + SQLite)

> **No database server needed.** SQLite is built into Python — the `cbpa.db` file is created automatically on first run inside `preprocessing_outputs/`.

1. Use Python 3.12+ and create/activate a virtual environment in `backend/`.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Copy env file and adjust if needed:

```bash
Copy-Item backend/.env.example backend/.env
```

4. Run the backend:

```bash
cd backend
uvicorn app.main:app --reload
```

## Frontend Setup

1. Install Node dependencies in project root:

```bash
npm install
```

2. Set API base URL in a root `.env` file:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

3. Run frontend:

```bash
npm run dev
```

## Model Artifacts

Place your trained artifacts in `backend/models/`:

- `model.joblib`
- `preprocessor.joblib`
- `feature_columns.json`

If artifacts are not present, backend uses a deterministic heuristic segmentation fallback so the UI still works.

## SQLite Storage

The backend uses a single SQLite file (`preprocessing_outputs/cbpa.db`) with two tables:

- **`datasets`** — stores full JSON payloads for customer and product analysis results, keyed by `datasetId`. Each upload is persisted with precomputed payloads for preview, dashboard, analysis, results, and insights.
- **`inventory_items`** — stores inventory as proper SQL rows for efficient row-level CRUD (add, edit quantity with +/− buttons, delete).

The frontend stores `datasetId` in local storage and automatically sends it with all GET calls.

## Inventory Management

The inventory catalog is backed directly by SQLite — no file upload required. It is seeded with default items on first run.

From the **Inventory Management** page you can:

- Add new items via the **+ Add Item** form (SKU, name, category, price, quantity, supplier)
- Adjust stock quantities instantly using the **+/−** buttons on each row
- Edit all fields of an item with the ✏️ button
- Delete items with the 🗑️ button
- Search by SKU / name / supplier and filter by category or stock status

Status badges (In Stock / Low Stock / Out of Stock) update automatically based on quantity.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+

### 1) Run Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### 2) Run Frontend (open a new terminal in project root)

```bash
npm install
npm run dev
```

### 3) Open App

- http://localhost:5173

---

## Environment Variables

| Variable                   | Default                         | Description                      |
| -------------------------- | ------------------------------- | -------------------------------- |
| `SQLITE_DB_PATH`           | `preprocessing_outputs/cbpa.db` | Path to the SQLite database file |
| `CORS_ORIGINS`             | `http://localhost:3000,...`     | Allowed frontend origins         |
| `MODEL_VERSION`            | `v1`                            | ML model version folder to load  |
| `PREPROCESSING_OUTPUT_DIR` | `preprocessing_outputs/`        | Directory for preprocessed CSVs  |

---

## Health Check

```
GET http://localhost:8000/health
→ { "status": "ok", "service": "Customer Buying Pattern Analysis API" }
```
