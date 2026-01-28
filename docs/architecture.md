# APISEC v1 Architecture

## Overview

APISEC v1 is an automated OpenAPI documentation generator that discovers or infers OpenAPI 3.x specifications from APIs.

## System Architecture

### Backend (FastAPI)

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── config.py        # Application configuration
│   │   └── security.py      # Authentication handling
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Pydantic request/response models
│   ├── services/
│   │   ├── openapi_fetcher.py  # Discover existing OpenAPI specs
│   │   ├── crawler.py          # Safe GET-only API crawling
│   │   ├── inferencer.py       # Infer OpenAPI spec from endpoints
│   │   └── report.py           # PDF report generation
│   ├── storage/
│   │   ├── specs/              # Stored OpenAPI JSON files
│   │   └── reports/            # Generated PDF reports
│   └── utils/
│       ├── http.py             # Safe HTTP client with rate limiting
│       └── validators.py       # OpenAPI validation utilities
└── requirements.txt
```

### Frontend (React)

```
frontend/
├── src/
│   ├── pages/
│   │   └── GenerateDocs.jsx    # Main page component
│   ├── components/
│   │   ├── ApiForm.jsx         # API URI input form
│   │   ├── Disclaimer.jsx     # Disclaimer component
│   │   └── ReportsList.jsx     # List of generated reports
│   └── services/
│       └── api.js              # Backend API client
└── package.json
```

## Workflow

1. **User Input**: User provides API URI and optional credentials
2. **Discovery**: System attempts to fetch existing OpenAPI spec from common paths
3. **Crawling** (if no spec found): Safe GET-only crawling to discover endpoints
4. **Inference**: Generate OpenAPI 3.x spec from discovered endpoints
5. **Storage**: Save OpenAPI JSON and generate PDF report
6. **Display**: Show results in UI

## Safety Constraints

- **NO destructive methods**: Only GET requests allowed
- **Rate limiting**: Configurable delay between requests
- **Depth limiting**: Maximum crawl depth to prevent infinite loops
- **Same-origin**: Only crawl same-domain endpoints
- **Error handling**: Graceful failure on errors

## Key Components

### OpenAPIFetcher

Attempts to discover existing OpenAPI specifications from common paths:
- `/openapi.json`
- `/swagger.json`
- `/v3/api-docs`
- `/api-docs`
- `/swagger/v1/swagger.json`

### SafeAPICrawler

Performs safe, GET-only crawling with:
- Rate limiting (0.5s default delay)
- Depth limiting (max 3 levels)
- Endpoint count limiting (max 50 endpoints)
- Same-origin validation
- Heuristic path discovery

### OpenAPIInferencer

Infers OpenAPI 3.x specification from discovered endpoints:
- Generates paths and operations
- Infers response schemas from JSON samples
- Marks inferred sections with `x-generated: "inferred"`
- Includes limitations in spec metadata

### PDFReportGenerator

Generates human-readable PDF reports with:
- API metadata
- Discovery method (existing vs inferred)
- Endpoint listing
- Known limitations
- Disclaimer text

## API Endpoints

- `POST /api/generate` - Generate documentation
- `GET /api/reports` - List all reports
- `GET /api/reports/{report_id}` - Download specific report
- `GET /api/specs/{spec_id}` - Get OpenAPI JSON spec

## Configuration

Key settings in `app/core/config.py`:
- `MAX_CRAWL_DEPTH`: Maximum crawl depth (default: 3)
- `MAX_ENDPOINTS`: Maximum endpoints to discover (default: 50)
- `RATE_LIMIT_DELAY`: Delay between requests in seconds (default: 0.5)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 10)

## Limitations

1. Only GET endpoints are discovered (safety constraint)
2. Auth-protected endpoints may not be accessible without credentials
3. Dynamic endpoints may not be detected
4. Response schemas are inferred from samples and may be incomplete
5. No support for POST/PUT/PATCH/DELETE endpoint discovery
