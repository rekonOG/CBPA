# Customer Buying Pattern Analysis

This project now includes:

- React frontend (`src/`)
- FastAPI backend with MongoDB storage (`backend/`)

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

## Backend Setup (FastAPI + MongoDB)

1. Start MongoDB locally (default URI: `mongodb://localhost:27017`).
2. Use Python 3.14 (or Python 3.12+) and create/activate a virtual environment in `backend/`.
3. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Copy env file and adjust if needed:

```bash
Copy-Item backend/.env.example backend/.env
```

5. Run the backend:

```bash
uvicorn backend.app.main:app --reload --port 8000
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
npm run start
```

## Model Artifacts

Place your trained artifacts in `backend/models/`:

- `model.joblib`
- `preprocessor.joblib`
- `feature_columns.json`

If artifacts are not present, backend uses a deterministic heuristic segmentation fallback so the UI still works.



## MongoDB Storage

Each upload is persisted with a generated `datasetId` and precomputed payloads for preview, dashboard, analysis, results, and insights.

The frontend stores `datasetId` in local storage and automatically sends it with all GET calls.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- MongoDB running on localhost

### 1) Run Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2) Run Frontend (open a new terminal in project root)

```powershell
npm install
npm run start
```

### 3) Open App

- http://localhost:3000
