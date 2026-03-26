# APISEC Project Context Document

This document provides a comprehensive overview of the APISEC project architecture, tech stack, database design, API structures, and core functional modules. It is designed to serve as foundational context for generating a well-structured project report.

## 1. Project Overview

APISEC is a web application and set of services focused on discovering API schemas, tracking versions, monitoring changes over time, and identifying runtime discrepancies. It includes an AI-enabled analyzer to interpret schema modifications and provide actionable remediation insights for breaking changes.

## 2. Technology Stack

### Backend
- **Framework**: FastAPI (Python) running on Uvicorn.
- **Data Validation & Serialization**: Pydantic, PyYAML.
- **HTTP/Networking**: Requests, aiohttp (for async requests).
- **AI Integration**: Google Generative AI (Gemini `gemini-2.5-flash`) for AI-powered schema diff insights.
- **PDF Generation**: ReportLab (to export schemas to PDF).

### Frontend
- **Framework**: React 19, initialized using Vite.
- **Routing**: React Router DOM.
- **Styling**: TailwindCSS, Autoprefixer, PostCSS.
- **Icons**: Lucide React.
- **Features**: Includes JWT session management (Login/Register views), an API dashboard, and a schema monitor with advanced search capabilities and on-demand "Analyze Diff" AI buttons.

### Infrastructure
- **Containerization**: Docker & Docker Compose (`docker-compose.yml` defining `apisec` backend and `nginx` proxying).
- **Database**: PostgreSQL

---

## 3. Database Design

The system uses PostgreSQL with a simple relational schema managed via raw SQL queries in `registry_db.py`.

### Tables

#### `users`
Manages authenticated identities for multi-tenant data isolation.
- `id` (SERIAL PRIMARY KEY)
- `username` (TEXT UNIQUE)
- `password_hash` (TEXT)
- `created_at` (TIMESTAMP)

#### `apis`
Tracks the registered API targets being monitored, isolated per user.
- `id` (SERIAL PRIMARY KEY)
- `user_id` (INTEGER): Foreign key linking to `users.id` (ON DELETE CASCADE).
- `name` (TEXT): Name of the API project.
- `base_url` (TEXT): Base URL for the target API.
- `description` (TEXT): Optional description.
- `date_added` (TEXT): ISO format timestamp.

#### `schema_snapshots`
Stores discovered schemas, linked to the APIs, simulating a version control system for schemas.
- `id` (INTEGER PRIMARY KEY)
- `api_id` (INTEGER): Foreign key linking to `apis.id` (ON DELETE CASCADE).
- `version_number` (INTEGER): Incrementing version ID per API.
- `schema_json` (TEXT): Serialized OpenAPI/Swagger JSON.
- `schema_pdf` (TEXT): Base64 encoded generated PDF representation of the schema.
- `timestamp` (TEXT): ISO format timestamp.

---

## 4. API Design & Endpoints

The FastAPI application (`main.py`) acts as the central hub connecting frontend and core modules. All core API and schema endpoints are secured via JWT bearer tokens to enforce user-level data isolation.

### Authentication APIs (`/auth`)
- **`POST /auth/register`**: Creates a new user account.
- **`POST /auth/login`**: Authenticates user credentials and issues a JWT access token.

### Internal Management APIs
- **`GET /api/apis`**: Returns all registered APIs.
- **`POST /api/apis`**: Creates a new API entry (expects form data: name, base_url, description).
- **`DELETE /api/apis/{api_id}`**: Deletes an API along with all its snapshot history.

### Schema Monitoring APIs
- **`GET /api/apis/{api_id}/schemas`**: Gets list of snapshot versions for an API.
- **`GET /api/apis/{api_id}/schemas/latest`**: Gets the most recent schema version.
- **`GET /api/schemas/{api_id}/version/{version}`**: Fetches a specific version snapshot.
- **`POST /api/apis/{api_id}/scan`**: Triggers a manual schema crawl for an API. If the schema has changed from the latest snapshot, a new version is saved and a backup PDF is generated.
- **`GET /api/schemas/{api_id}/compare/{version1}/{version2}`**: Generates a differential analysis between two schema versions. Supports both legacy formatting and newer structured formatting (`?structured=True`).

### Analysis & Runtime Operations
- **`POST /discover-schema`**: Crawls an ad-hoc URL to discover and return an existing OpenAPI/Swagger JSON/YAML schema.
- **`POST /validate-runtime`**: Accepts a base URL and schema JSON. The `RuntimeValidator` spins up concurrent requests testing identified endpoints, tracking real responses against expected schema boundaries.
- **`POST /api/schemas/{api_id}/analyze-change`**: Initiates a detailed, AI-powered generation of impact and remediation steps for a *specific* schema code diff using Google Gemini.
- **`POST /analyze-diff`**: Placeholder endpoint for live endpoint vs endpoint differences utilizing the Differential Engine.

---

## 5. Core Modules & Algorithms

The backend contains several robust analytical modules designed to parse, analyze, and test API endpoints.

### A. Schema Monitor & Crawler (`schema_monitor.py`)
- **Discovery Algorithm (`crawl_for_schema`)**:
  - Tries appending common API spec paths (`/openapi.json`, `/swagger.json`, `/docs`, etc.) in order of priority to find a valid OpenAPI/Swagger schema.
  - If direct requests fail, falls back to parsing HTML (`discover_schema_from_html`) from the root URL to extract `<link>` and `<script>` components that might point to or contain the embedded schema.
- **Normalization Engine (`normalize_schema`)**:
  - Detaches irrelevant metadata strings (descriptions, tags, summaries) that don't affect code contracts.
  - Recursively resolves JSON `$ref` imports.
  - Deterministically sorts dictionary keys to establish a static, diff-friendly baseline.
- **Diffing Algorithm (`compare_schemas_detailed` / `compare_request_body_schemas`)**:
  - Traverses the entire JSON tree comparing properties, tracking added, removed, or modified types and required fields.
  - Generates detailed object trajectories matching differences (e.g., changes from low severity type swaps to high severity removal of required config fields).

### B. AI Analyzer (`ai_analyzer.py`)
- **Semantic Prompt Composition (`_build_prompt` / `analyze_single_change`)**:
  - Condenses large OpenAPI definitions utilizing `_summarize_schema`, which truncates excessively large nested request responses.
  - Injects changes detected by the standard differ into the Google Gemini GenAI prompt.
  - Gemini translates the diff into 3 segments: 
    1. Human-readable description.
    2. Impact analysis on consumers/SDKs.
    3. Actionable fix suggestions (specifically for breaking changes).

### C. Runtime Validator (`runtime_validator.py`)
- **Constraint Generation (`_test_endpoint`)**:
  - Recursively climbs schema trees deriving test parameters (`_generate_sample_value_for_param`).
  - Utilizes deterministic seeds tied to method + path + parameter name ensuring repeatable hashing boundaries.
  - Asynchronously requests all API endpoint variants scaling concurrency limits via semaphores (`aiohttp`).
- **Response Auditing (`_validate_response_schema`)**:
  - Receives payload and evaluates response HTTP status bounds.
  - Detects deviations between the expected parameter structures vs returned JSON keys/data types.

### D. Differential Probing Engine (`probes/differential_engine.py`)
- **Behavioral Footprinting (`ResponseFingerprint` / `FingerprintDiff`)**:
  - Rather than focusing entirely on OpenAPI schemas, this module blasts endpoints to track error behavior.
  - Grabs a baseline request.
  - Utilizes `StringProbe`, `NumericProbe`, and `BooleanProbe` variations to fuzzy-inject candidates recursively into endpoint bodies (`_test_candidate_parameter`).
  - Uses `compare_fingerprints` and `extract_error_patterns_from_fingerprint` to locate hidden/undocumented parameters in error output messages (FastAPI's `"loc"`, parameter 'X' missing patterns) and hashes behavioral variances marking them as a `ParameterCandidate`.

---

## 6. Testing Strategy & Execution

### A. Unit Testing
The backend relies on `pytest` to execute isolated component validations (e.g., verifying `test_schema_diffing.py`). Unit tests rigorously evaluate exact matching of expected JSON dictionaries, API schema validation models, and core generic functions without requiring active network payloads or a running Uvicorn server.

### B. Integration Testing
Tests like `test_enhanced_validator.py` and `test_runtime_validator.py` act as integration tests. They test the interplay between the `DifferentialEngine`, error pattern extractions, fingerprint mechanisms, and the database interfaces (`ApiRegistry`, `SchemaSnapshot`). Mock dependencies or local isolated environments are required to simulate PostgreSQL and external REST APIs interactions optimally.

### C. Functional Testing
Functional testing evaluates specific behaviors critical to user experiences. For example, testing validates that uploading a malformed or breaking schema correctly triggers the Gemini (`gemini-2.5-flash`) semantic parser, constructing specific impact analysis outputs rather than raw stack traces. It guarantees schema isolation mapping via individual JWT tokens.

### D. Load Testing
Load handling for the FastAPI environment is continuously evaluated and measured natively via `Locust`. Tests simulate aggressive parallel requests to `POST /api/auth/login` and `GET /api/schemas/changes`, verifying that the asynchronous worker threads natively route high-volume diff generations and massive database calls without starving the server event loop synchronously.
