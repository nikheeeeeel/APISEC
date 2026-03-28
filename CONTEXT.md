# APISEC Project Context Document

## Project Overview

APISEC is a comprehensive API security toolkit for discovering API schemas, tracking versions, and analyzing differences between API endpoints. It provides both automated schema discovery and differential analysis capabilities with a modern web interface.

## Architecture

### Backend (FastAPI)
- **Main Server**: `backend/main.py` - FastAPI application with CORS, authentication, and API endpoints
- **Database**: PostgreSQL with SQLAlchemy ORM (migrated from SQLite)
- **Authentication**: JWT-based auth with OAuth support (Google, GitHub)
- **Schema Discovery**: `backend/schema_monitor.py` - Crawls APIs for OpenAPI/Swagger schemas
- **Differential Analysis**: `backend/probes/differential_engine.py` - Compares API schemas
- **Response Fingerprinting**: `backend/fingerprint/response_fingerprint.py` - Creates response signatures
- **Runtime Validation**: `backend/runtime_validator.py` - Validates API responses against schemas

### Frontend (React + Vite)
- **Framework**: React 19 with Vite build system
- **UI**: TailwindCSS for styling, Lucide React for icons
- **Routing**: React Router DOM for navigation
- **Location**: `frontend-react/` directory

### Infrastructure
- **Containerization**: Docker with docker-compose setup
- **Reverse Proxy**: Nginx for production deployment
- **Database**: PostgreSQL 15 with persistent volumes
- **Health Checks**: Configured for all services

## Key Features

1. **Schema Discovery**
   - Automatically detects OpenAPI/Swagger schemas
   - Supports common endpoints: `/schema`, `/openapi`, `/swagger`, etc.
   - Saves schema snapshots with version tracking

2. **Differential Analysis**
   - Compares two API endpoints
   - Identifies breaking changes
   - Generates detailed diff reports

3. **Runtime Validation**
   - Validates actual API responses against schemas
   - Detects schema violations in real-time
   - Generates compliance reports

4. **Authentication & Authorization**
   - JWT token-based authentication
   - OAuth integration (Google, GitHub)
   - User management system

## API Endpoints

### Core API Routes
- `GET /health` - Health check
- `POST /discover-schema` - Discover schema from URL
- `POST /analyze-diff` - Compare two API endpoints
- `POST /runtime-validate` - Validate API responses

### Authentication Routes
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/oauth/{provider}` - OAuth initiation
- `GET /auth/oauth/callback/{provider}` - OAuth callback

### Registry Routes
- `GET /registry/apis` - List registered APIs
- `POST /registry/apis` - Register new API
- `GET /registry/apis/{api_id}/snapshots` - Get API version history

## Database Schema

### Core Tables
- `users` - User authentication data
- `api_registry` - Registered API endpoints
- `schema_snapshots` - Versioned schema snapshots
- `validation_results` - Runtime validation results

### Models Location
- `backend/models.py` - Core data models
- `backend/user_models.py` - User-related models
- `backend/models_runtime.py` - Runtime validation models

## Development Setup

### Backend Development
```bash
cd backend
pip install -r requirements.txt
python main.py  # Starts on http://localhost:8000
```

### Frontend Development
```bash
cd frontend-react
npm install
npm run dev  # Starts on http://localhost:5173
```

### Full Stack Development
```bash
docker-compose up  # Starts all services
```

## Configuration

### Environment Variables
- `JWT_SECRET_KEY` - JWT signing key
- `GOOGLE_CLIENT_ID/SECRET` - Google OAuth credentials
- `GITHUB_CLIENT_ID/SECRET` - GitHub OAuth credentials
- `DATABASE_URL` - PostgreSQL connection string

### Config Files
- `backend/config.py` - Application configuration
- `backend/.env` - Environment variables (create from .env.example)
- `docker-compose.yml` - Service orchestration

## Testing

### Backend Tests
- Located in `backend/tests/`
- Uses pytest with async support
- Includes integration tests with testcontainers
- Run with: `pytest backend/`

### Frontend Tests
- Playwright for end-to-end testing
- ESLint for code quality

## Key Dependencies

### Backend
- FastAPI - Web framework
- SQLAlchemy - Database ORM
- Pydantic - Data validation
- Requests/aiohttp - HTTP clients
- ReportLab - PDF generation
- python-jose - JWT handling

### Frontend
- React 19 - UI framework
- Vite - Build tool
- TailwindCSS - Styling
- React Router - Navigation
- Lucide React - Icons

## Security Features

1. **Input Validation** - All inputs validated with Pydantic models
2. **Authentication** - JWT tokens with expiration
3. **CORS** - Properly configured for frontend-backend communication
4. **SQL Injection Prevention** - SQLAlchemy ORM usage
5. **Rate Limiting** - Can be implemented via middleware

## Deployment

### Production Deployment
- Uses Docker containers
- Nginx reverse proxy on ports 80/443
- PostgreSQL database with persistent storage
- Health checks for all services
- Environment-based configuration

### Database Migration
- Migration script: `migrate_to_postgres.py`
- Handles SQLite to PostgreSQL migration
- Preserves existing data

## File Structure Highlights

```
apisec/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main application server
│   ├── schema_monitor.py      # Schema discovery logic
│   ├── registry_db.py         # Database operations
│   ├── probes/                # Differential analysis
│   ├── fingerprint/           # Response fingerprinting
│   └── tests/                 # Backend tests
├── frontend-react/            # React frontend
│   ├── src/                   # React source code
│   ├── package.json           # Frontend dependencies
│   └── vite.config.js         # Build configuration
├── docker-compose.yml         # Service orchestration
├── nginx.conf                 # Reverse proxy config
└── CONTEXT.md                 # This context document
```

## Common Development Tasks

1. **Adding New API Endpoints**: Modify `backend/main.py` and corresponding models
2. **Database Changes**: Update models in `backend/models.py` and run migrations
3. **Frontend Components**: Add to `frontend-react/src/components/`
4. **Testing**: Add tests to `backend/tests/` or use Playwright for frontend
5. **Configuration**: Update `backend/config.py` for new settings

## Debugging Tips

- Backend logs: Check console output when running `python main.py`
- Database issues: Verify PostgreSQL connection in docker-compose
- Frontend build issues: Check Vite dev server logs
- CORS problems: Verify CORS middleware configuration in `main.py`

## Performance Considerations

- Schema discovery can be resource-intensive for large APIs
- Database queries optimized with proper indexing
- Frontend uses React.memo and useMemo for performance
- Async/await patterns used throughout backend

This context document provides a comprehensive overview of the APISEC project structure, functionality, and development workflow.
