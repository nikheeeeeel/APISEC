# API Schema Discovery & Diffing

A minimal web application for discovering API schemas, tracking versions, and analyzing differences between API endpoints.

## Features

- **Schema Discovery**: Automatically discover API schemas from common endpoints (`/schema`, `/openapi`, `/swagger`, etc.)
- **Version Tracking**: Store and track multiple versions of API schemas
- **Differential Analysis**: Compare two API endpoints and analyze differences
- **Single Page Interface**: Clean, responsive web interface for all operations

## Project Structure

```
apisec/
├── frontend/
│   └── index.html              # Single-page web application
├── backend/
│   ├── __init__.py            # Module exports
│   ├── main.py                # FastAPI server
│   ├── schema_monitor.py      # Schema discovery logic
│   ├── registry_db.py         # Database operations
│   ├── models.py              # Data models
│   ├── fingerprint/           # Response fingerprinting
│   │   ├── __init__.py
│   │   └── response_fingerprint.py
│   └── probes/                # Differential analysis
│       ├── __init__.py
│       ├── differential_engine.py
│       └── strategies.py
└── README.md
```

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Backend Server
```bash
cd backend
python main.py
```

The server will start on `http://localhost:8000`

### 3. Access the Web Interface
Open your browser and navigate to `http://localhost:8000`

## Usage

### Discover API Schema
1. Enter an API URL (e.g., `https://api.example.com`)
2. Click "Discover Schema"
3. View the discovered schema and save it to version history

### Compare Two APIs
1. Enter base API URL and new API URL
2. Click "Compare APIs"
3. View the differential analysis results

### View Version History
- Browse all discovered schemas
- Compare different versions
- View detailed schema information

## API Endpoints

### Backend API
- `GET /health` - Health check
- `POST /discover-schema` - Discover schema from URL
- `POST /analyze-diff` - Compare two API endpoints

### Frontend
- `/` - Main web interface (served from `frontend/index.html`)

## Dependencies

### Backend
- **FastAPI** - Web framework
- **Requests** - HTTP client for API calls
- **ReportLab** - PDF generation
- **PyYAML** - YAML parsing
- **Pydantic** - Data validation

### Frontend
- **Vue.js 3** - Reactive frontend framework
- **Axios** - HTTP client for API calls
- No build step required - uses CDN versions

## Database

The application uses SQLite (`apisec.db`) for storing schema snapshots and version history. The database is created automatically on first run.

## Development

### Backend Development
```bash
cd backend
python main.py  # Start development server
```

### Frontend Development
The frontend is a single HTML file with no build process required. Simply open `frontend/index.html` in a browser or access via the backend server at `http://localhost:8000`.

## License

Part of the API Security toolkit.
