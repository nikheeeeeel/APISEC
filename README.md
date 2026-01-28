# APISEC v1

Automated OpenAPI Documentation Generator - Discover or infer OpenAPI 3.x specifications from APIs.

## Overview

APISEC v1 is a near-production-grade system for automated OpenAPI documentation generation. It can:

- **Discover** existing OpenAPI/Swagger documentation from common paths
- **Infer** OpenAPI 3.x specifications through safe API crawling (GET-only)
- **Generate** human-readable PDF reports
- **Store** OpenAPI JSON specifications and reports

## ⚠️ Important Disclaimers

- Documentation is generated on a **best-effort basis**
- May be **incomplete or inaccurate**
- **Auth-protected endpoints** may not be detected without credentials
- **Dynamic endpoints** may not be discovered
- Only **GET endpoints** are discovered (safety constraint)
- Non-GET endpoints (POST, PUT, PATCH, DELETE) are **not** discovered

## Features

- ✅ Automatic OpenAPI discovery from common paths
- ✅ Safe GET-only API crawling with rate limiting
- ✅ OpenAPI 3.x specification inference
- ✅ PDF report generation
- ✅ Web UI for easy interaction
- ✅ Secure credential handling (never stored in plaintext)
- ✅ Same-origin crawling safety

## Project Structure

```
apisec/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py       # FastAPI application
│   │   ├── core/         # Configuration and security
│   │   ├── api/          # API routes and schemas
│   │   ├── services/     # Business logic services
│   │   ├── storage/      # Generated specs and reports
│   │   └── utils/        # Utility functions
│   └── requirements.txt
├── frontend/             # React frontend
│   └── src/
│       ├── pages/        # Page components
│       ├── components/   # UI components
│       └── services/     # API client
└── docs/                 # Documentation
```

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Usage

### Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

### Start Frontend

```bash
cd frontend
npm start
```

Frontend will be available at `http://localhost:3000`

### API Usage

#### Generate Documentation

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "api_uri": "https://api.example.com",
    "api_key": "optional-key",
    "bearer_token": "optional-token"
  }'
```

#### List Reports

```bash
curl http://localhost:8000/api/reports
```

#### Download Report

```bash
curl http://localhost:8000/api/reports/{report_id} -o report.pdf
```

## How It Works

1. **Discovery Phase**: Attempts to fetch existing OpenAPI spec from:
   - `/openapi.json`
   - `/swagger.json`
   - `/v3/api-docs`
   - `/api-docs`
   - `/swagger/v1/swagger.json`

2. **Crawling Phase** (if no spec found):
   - Performs safe GET-only crawling
   - Rate-limited requests (0.5s delay)
   - Depth-limited (max 3 levels)
   - Same-origin validation
   - Heuristic endpoint discovery

3. **Inference Phase**: Generates OpenAPI 3.x spec from discovered endpoints

4. **Report Generation**: Creates PDF report with endpoint listing and metadata

## Safety Constraints

- ✅ **NO destructive HTTP methods** - Only GET requests
- ✅ **Rate limiting** - Configurable delay between requests
- ✅ **Depth limiting** - Prevents infinite crawling
- ✅ **Same-origin** - Only crawls same-domain endpoints
- ✅ **Error handling** - Graceful failure on errors

## Configuration

Edit `backend/app/core/config.py` to adjust:

- `MAX_CRAWL_DEPTH`: Maximum crawl depth (default: 3)
- `MAX_ENDPOINTS`: Maximum endpoints (default: 50)
- `RATE_LIMIT_DELAY`: Delay between requests in seconds (default: 0.5)
- `REQUEST_TIMEOUT`: HTTP timeout in seconds (default: 10)

## Limitations

- Only GET endpoints are discovered
- Auth-protected endpoints require credentials
- Dynamic endpoints may not be detected
- Response schemas are inferred and may be incomplete
- No support for discovering POST/PUT/PATCH/DELETE endpoints

## License

See LICENSE file for details.

## Contributing

This is v1 scope. Future enhancements may include:
- Support for additional HTTP methods (with user consent)
- Enhanced schema inference
- OpenAPI spec validation and enhancement
- Integration with API testing tools
