# APISEC Backend

FastAPI backend for automated OpenAPI documentation generation.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Storage

Generated files are stored in:
- `app/storage/specs/` - OpenAPI JSON specifications
- `app/storage/reports/` - PDF reports

These directories are created automatically on first run.

## Environment Variables

Create a `.env` file in the backend directory to override default settings:

```env
MAX_CRAWL_DEPTH=3
MAX_ENDPOINTS=50
RATE_LIMIT_DELAY=0.5
REQUEST_TIMEOUT=10
```
