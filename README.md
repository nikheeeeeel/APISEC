# APISec - Advanced API Parameter Discovery System

A comprehensive parameter inference system that discovers missing parameters in APIs through automated analysis, providing developers with complete API specifications without manual documentation.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- FastAPI and required dependencies (see `requirements.txt`)
- Node.js 18+
- Modern web browser

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd apisec

# Create a virtual environment for the backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend and test API dependencies
cd frontend
npm install
cd ../test_api
npm install
cd ..
```

### Running the stack for a live presentation
1. **Start the backend**
   ```bash
   cd backend
   python server.py
   ```
2. **Launch the demo/test API**
   ```bash
   cd test_api
   npm start
   ```
   This Express server (http://localhost:5050) surfaces query, body, header, and path validation workloads that highlight the inference features.
3. **Run the frontend**
   ```bash
   cd frontend
   npm run dev
   ```
   The Vite server defaults to `http://localhost:3000` and proxies `/api/*` to `http://localhost:8000`. `frontend/.env` already sets `VITE_API_BASE_PATH=/api`.
4. **Drive the demo**
   Point the inference form to the local test API endpoints (see table below) to show parameter discovery, location signals, and spec export in one flow.

### CLI Interface (optional)
```bash
cd backend
python -m backend.cli --url https://api.example.com/endpoint --method POST --time 30

python -m backend.cli --url https://api.example.com/endpoint --method POST --time 30 > spec.json
```

### Demo/test API (presentation target)
When presenting, use the built-in Express service at `http://localhost:5050` so the frontend can demonstrate query/body/path/header discovery. The server intentionally returns structured validation errors (missing field lists, unauthorized responses) so APISec shows parameter evidence.

| Endpoint | Method | Demo focus | Required input |
| --- | --- | --- | --- |
| `/users?email=<value>` | GET | Query discovery + error message | Query `email` |
| `/search?q=<term>` | GET | Additional query hit with synthetic results | Query `q` |
| `/login` | POST | Body validation for `username` + `password` | JSON body with `username`, `password` |
| `/orders` | POST | Body validation across `orderId`, `quantity`, `shippingAddress` | JSON body with all three keys |
| `/items/:itemId` | GET | Path parameter inference with numeric ID | URL like `/items/42` |
| `/users/:userId/status` | PATCH | Mixed path + body (`status`) | JSON body `{"status": "active"}` |
| `/secure-data` | GET | `Authorization: Bearer testtoken` header | Header `Authorization: Bearer testtoken` |
| `/reports` | GET | Custom header validation (`X-Report-Token`) | Header `X-Report-Token: report123` |

You can rapidly toggle between these targets with the UI’s URL field and time limit controls, then export the generated OpenAPI spec for the audience to inspect.

## 🧠 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    APISec Inference System                │
├─────────────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Web UI    │    │   FastAPI   │    │  Backend  │ │
│  │  (Browser)   │────│   Server    │────│  Logic    │ │
│  └─────────────┘    └──────────────┘    └───────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           Inference Pipeline                      │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │   │
│  │  │ Error Probe │  │  Type Probe  │  │Location  │ │   │
│  │  │             │  │             │  │ Probe  │ │   │
│  │  └─────────────┘  └──────────────┘  └─────────┘ │   │
│  │                   ┌──────────────┐  ┌─────────────┐ │   │
│  │                   │ Confidence   │  │ Spec Generator│ │   │
│  │                   │ Engine      │  │             │ │   │
│  │                   └──────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────────────┘
```

## 🔍 Core Components

### 1. Error Probe (`backend/inference/error_probe.py`)
**Purpose**: Discover parameter names from API error messages

**How it works**:
- Sends minimal JSON payloads to target endpoint
- Analyzes validation errors for parameter references
- Uses regex patterns to extract parameter names from FastAPI-style errors
- Iteratively mutates payloads to discover new parameters
- Stops when no new parameters are found

**Key Features**:
- **Non-intrusive**: Only analyzes error responses, never modifies target API
- **Pattern-based**: Uses sophisticated regex to parse various error formats
- **Evidence collection**: Stores error text, status codes, and patterns used
- **Confidence scoring**: Assigns confidence based on discovery method

**Output Example**:
```json
{
  "username": {
    "required": true,
    "confidence": 0.7,
    "evidence": [
      {
        "error_text": "Field 'username' is required",
        "status_code": 422,
        "pattern": "username"
      }
    ]
  }
}
```

### 2. Type Probe (`backend/inference/type_probe.py`)
**Purpose**: Infer parameter types and constraints through safe testing

**How it works**:
- Tests one parameter at a time with minimal payloads
- Sends predefined test values: "test", 1, true, null, {}
- Analyzes response differences to infer types
- Applies strict safety constraints (max 5 requests per parameter)
- Never attempts to discover new parameters

**Test Matrix**:
| Test Value | Expected Type | Inference Logic |
|------------|---------------|----------------|
| "test"     | string         | If accepted → string type |
| 1           | number         | If accepted → number type |
| true        | boolean        | If accepted → boolean type |
| null        | nullable       | If accepted → nullable true |
| {}          | object         | If accepted → object type |

**Safety Features**:
- **Bounded requests**: Maximum 5 requests per parameter
- **Time limits**: Respects global timeout constraints
- **Error isolation**: Failure of one parameter doesn't affect others
- **Graceful degradation**: Returns "unknown" type if inference fails

### 3. Location Probe (`backend/inference/location_probe.py`)
**Purpose**: Determine where parameters belong (query, body, path, header)

**How it works**:
- **Query Test**: Sends `?param=test` and checks for query parameter references
- **Body Test**: Sends `{"param": "test"}` and checks for body field references  
- **Path Heuristic**: Analyzes URL patterns like `/users/{id}` without making requests
- **Header Test**: Sends `X-param: test` with conservative validation

**Location Mapping**:
- **query** → OpenAPI `parameters` with `in: "query"`
- **body** → OpenAPI `requestBody` with JSON schema
- **path** → OpenAPI `parameters` with `in: "path"`
- **header** → OpenAPI `parameters` with `in: "header"`
- **unknown** → Included with `x-location: "unknown"`

**Confidence Scoring**:
- Explicit parameter reference: +0.5
- Path pattern match: 0.9
- Header mention: +0.6
- Generic error: +0.1
- Conflicting signals: -0.3

### 4. Confidence Engine (`backend/inference/confidence.py`)
**Purpose**: Merge signals from all probes into unified confidence scores

**How it works**:
- **Signal aggregation**: Combines evidence from error, type, and location probes
- **Weighted scoring**: Applies different weights to different evidence types
- **Conflict detection**: Reduces confidence when probes disagree
- **Deterministic output**: Same inputs always produce same confidence scores

**Scoring Rules**:
```
Base confidence: 0.2 (if parameter exists)
+ Structured validation error: +0.3
+ Multiple parameter references: +0.2  
+ Required inference: +0.1
+ Type inferred (not unknown): +0.2
- Conflicting evidence: -0.2
- Only generic errors: -0.1
Final range: [0.1 - 1.0]
```

### 5. Orchestrator (`backend/inference/orchestrator.py`)
**Purpose**: Coordinate all probes with time bounds and safety constraints

**How it works**:
- **Sequential execution**: Runs error_probe → type_probe for each discovered parameter
- **Time management**: Enforces global timeout and per-parameter limits
- **Partial failure handling**: Continues even if individual probes fail
- **Result aggregation**: Merges all evidence into unified output

**Safety Features**:
- **Global timeout**: Stops all inference when time limit exceeded
- **Per-parameter timeout**: Respects remaining time for each parameter
- **Exception isolation**: Failure of one probe doesn't stop others
- **Graceful degradation**: Always returns valid structure

### 6. Spec Generator (`backend/spec/generator.py`)
**Purpose**: Transform inference results into OpenAPI 3.0 specifications

**How it works**:
- **Parameter grouping**: Separates parameters by location (query, body, path, header)
- **Schema generation**: Creates proper OpenAPI schemas for each parameter
- **Extension preservation**: Maintains `x-*` extensions for confidence and evidence
- **Server detection**: Extracts base URL from inference target

**Output Structure**:
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Inferred API Spec",
    "version": "0.1.0",
    "x-inference-meta": {
      "total_parameters": 5,
      "execution_time_ms": 2500
    }
  },
  "paths": {
    "/endpoint": {
      "post": {
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "username": {
                    "type": "string",
                    "x-confidence": 0.85
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## 🌐 Web Interface

### Access Methods

#### Method 1: Direct File Access
```bash
# Open the UI file directly in your browser
open ui/index.html
# or double-click the file in your file manager
```

#### Method 2: Local HTTP Server (Recommended)
```bash
# Navigate to the UI directory
cd ui

# Start a simple HTTP server
python -m http.server 3000

# Open your browser to:
http://localhost:3000
```

### UI Features

#### 📝 Input Form
- **Target URL**: Required API endpoint with real-time validation
- **HTTP Method**: Dropdown selection (GET/POST) with proper defaults
- **Time Limit**: Optional timeout setting (1-120 seconds, default: 30)
- **Smart validation**: URL format checking before submission

#### 🎯 Action Buttons
- **Run Inference**: Executes complete parameter discovery pipeline
- **Generate OpenAPI Spec**: Creates API documentation from inference results
- **Real-time feedback**: Loading states and progress indicators

#### 📊 Results Display
- **Summary Dashboard**: Parameters found, execution time, failure count
- **Parameter Details**: Name, location, type, required, nullable, confidence
- **Evidence Trail**: Complete audit trail for each discovered parameter
- **Confidence Visualization**: Color-coded badges (green=high, yellow=medium, red=low)

#### 📥 Download Options
- **inference.json**: Raw inference results with all metadata
- **openapi.json**: Generated API specification in OpenAPI 3.0 format
- **Client-side generation**: No server-side file writes for security

#### 🛡️ Error Handling
- **User-friendly messages**: Clear, actionable error descriptions
- **Input validation**: Real-time feedback for invalid URLs or methods
- **Backend connectivity**: Health checks with connection status
- **Graceful degradation**: Always shows partial results when available

### UI Workflow Example

1. **Enter Target**: `https://api.example.com/users`
2. **Select Method**: `POST`
3. **Set Timeout**: `30` seconds
4. **Click "Run Inference"**
5. **Monitor Progress**: Watch real-time status updates
6. **Review Results**: Examine discovered parameters with confidence scores
7. **Download Results**: Save inference.json and openapi.json files
8. **Generate Documentation**: Click "Generate OpenAPI Spec" for API docs

## 🔧 CLI Interface

### Basic Usage
```bash
# Simple inference
python -m backend.cli --url https://api.example.com/endpoint --method POST

# With custom timeout
python -m backend.cli --url https://api.example.com/endpoint --method POST --time 60

# Output to file
python -m backend.cli --url https://api.example.com/endpoint --method POST > results.json
```

### Advanced Options
- **`--url`**: Target API endpoint (required)
- **`--method`**: HTTP method, GET or POST (default: POST)
- **`--time`**: Maximum execution time in seconds (default: 30)

### Output Format
```json
{
  "url": "https://api.example.com/endpoint",
  "method": "POST",
  "parameters": [
    {
      "name": "username",
      "location": "body",
      "required": true,
      "type": "string",
      "nullable": false,
      "confidence": 0.85,
      "evidence": [...]
    }
  ],
  "meta": {
    "total_parameters": 1,
    "partial_failures": 0,
    "execution_time_ms": 2500,
    "error_probe_time_ms": 800,
    "type_inference_time_ms": 1200,
    "time_limit_seconds": 30
  }
}
```

## 🏗️ HTTP API Service

### Starting the Service
```bash
cd backend
python server.py
# Server runs on http://127.0.0.1:8000
```

### API Endpoints

#### Health Check
```bash
GET /health
```
**Response**:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

#### Parameter Inference
```bash
POST /infer
Content-Type: application/json

{
  "url": "https://api.example.com/endpoint",
  "method": "POST",
  "time": 30
}
```

#### OpenAPI Generation
```bash
POST /spec
Content-Type: application/json

{
  "url": "https://api.example.com/endpoint", 
  "method": "POST",
  "time": 30
}
```

### Features
- **CORS enabled**: Cross-origin requests supported for web UI
- **Input validation**: Pydantic models ensure valid requests
- **Error handling**: Structured error responses, no stack traces
- **Time bounds**: Enforces execution limits for safety
- **JSON responses**: Consistent output format for all endpoints

## 🔍 Inference Engine Status

### Current Implementation
**Arjun Integration**: The system currently **does not use Arjun** for parameter discovery. Instead, it uses a custom error-driven inference approach that provides:

#### Advantages Over Arjun:
- **Evidence-based**: Every discovered parameter includes supporting evidence
- **Type inference**: Determines parameter types, not just names
- **Location detection**: Identifies where parameters belong (query, body, path, header)
- **Confidence scoring**: Provides reliability metrics for each parameter
- **Safety constraints**: Bounded requests, time limits, graceful failure handling

#### When to Use Arjun:
- **High-confidence discovery**: If error-driven inference finds no parameters
- **Comprehensive scanning**: For APIs with many undocumented parameters
- **Complementary approach**: Use Arjun as fallback when inference confidence is low

### Future Integration Strategy

#### Hybrid Approach (Recommended):
```python
# 1. Run error-driven inference first
inference_result = orchestrate_inference(url, method, time_limit)

# 2. Check confidence levels
low_confidence_params = [p for p in inference_result['parameters'] if p['confidence'] < 0.5]

# 3. If low confidence, supplement with Arjun
if len(low_confidence_params) > 0:
    arjun_result = run_arjun_discovery(url, method)
    merged_result = merge_inference_results(inference_result, arjun_result)
```

#### Integration Benefits:
- **Best of both worlds**: Evidence-driven + comprehensive scanning
- **Confidence-aware**: Only use Arjun when needed
- **Result merging**: Combine evidence from both approaches
- **Fallback safety**: Always have some parameter discovery

## 📊 Performance Characteristics

### Speed
- **Fast endpoints**: 2-5 seconds for simple APIs
- **Complex APIs**: 10-30 seconds for comprehensive discovery
- **Timeout handling**: Respects user-defined time limits
- **Parallel ready**: Can be extended for concurrent processing

### Accuracy
- **High confidence**: 0.8+ for well-documented APIs
- **Medium confidence**: 0.5-0.8 for partially documented APIs
- **Low confidence**: 0.1-0.5 for poorly documented APIs
- **Evidence quality**: Rich audit trails for all discoveries

### Resource Usage
- **Memory efficient**: Minimal state, no large data retention
- **Network conscious**: Bounded request patterns, rate-limit friendly
- **CPU light**: Simple string processing and JSON parsing
- **Storage minimal**: No file writes unless explicitly requested

## 🛡️ Security & Safety

### Design Principles
- **No authentication**: Never attempts credential inference
- **No persistence**: Results stored in memory only
- **Bounded execution**: Time and request limits enforced
- **Error isolation**: Failures don't crash the system
- **Input validation**: All user inputs validated and sanitized

### Privacy Features
- **No data logging**: API endpoints and parameters not stored
- **Client-side processing**: Downloads generated in browser only
- **Ephemeral results**: Data cleared on page refresh
- **Secure defaults**: No sensitive information in default configurations

## 🔧 Development

### Project Structure
```
apisec/
├── backend/
│   ├── inference/
│   │   ├── error_probe.py      # Error-based parameter discovery
│   │   ├── type_probe.py       # Type and constraint inference
│   │   ├── location_probe.py    # Parameter location detection
│   │   ├── confidence.py       # Confidence scoring engine
│   │   └── orchestrator.py    # Pipeline coordination
│   ├── spec/
│   │   └── generator.py       # OpenAPI spec generation
│   ├── server.py              # FastAPI HTTP service
│   ├── app.py                # Core inference function
│   ├── cli.py                # Command-line interface
│   └── main.py               # Original FastAPI app
├── ui/
│   ├── index.html             # Web interface
│   ├── app.js                # Client-side JavaScript
│   └── README.md              # UI documentation
├── requirements.txt           # Python dependencies
└── README.md               # This file
```

### Adding New Probes
1. **Create probe module** in `backend/inference/`
2. **Implement standard interface** with input/output contracts
3. **Add to orchestrator** for pipeline integration
4. **Update confidence engine** to handle new evidence types
5. **Add tests** to validate probe behavior

### Testing
```bash
# Run comprehensive test suite
python run_tests.py

# Individual component tests
python -m pytest tests/

# Integration tests
python -m pytest integration/
```

## 📝 Configuration

### Environment Variables
```bash
# Optional: Custom backend port
export APISEC_PORT=8000

# Optional: Custom UI port  
export APISEC_UI_PORT=3000

# Optional: Default timeout
export APISEC_DEFAULT_TIMEOUT=30
```

### Customization
- **Probe weights**: Adjust confidence scoring in `confidence.py`
- **Timeout values**: Modify defaults in `orchestrator.py`
- **Test patterns**: Update regex patterns in `error_probe.py`
- **UI styling**: Modify Tailwind classes in `ui/index.html`

## 🤝 Contributing

### Development Workflow
1. **Fork repository** and create feature branch
2. **Add tests** for new functionality
3. **Update documentation** for API changes
4. **Ensure all tests pass** before submitting PR
5. **Follow code style** and architectural patterns

### Guidelines
- **Deterministic**: Same inputs must produce same outputs
- **Evidence-based**: All discoveries must include supporting evidence
- **Safe defaults**: Never expose sensitive information
- **Clear documentation**: Update README for all changes
- **Test coverage**: Maintain high test coverage for inference logic

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🆘 Support

For issues, questions, or contributions:
- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs with detailed reproduction steps
- **Features**: Request enhancements with use case descriptions
- **Security**: Report security concerns privately

---

**APISec** provides a comprehensive, evidence-based approach to API parameter discovery that goes beyond traditional tools, offering developers deeper insights into API structures with confidence metrics and detailed evidence trails.
