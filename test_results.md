# APISec Test Results Documentation

## Overview
This document contains 3 test cases ranging from best case to worst case for the APISec parameter inference project.

---

## Test Case 1: Best Case - Ideal FastAPI Endpoint

### Description
Tests against a well-behaved FastAPI endpoint with clear validation errors and proper parameter discovery.

### Test Setup
```python
# Target endpoint: http://127.0.0.1:8001/api/typed
# Expected parameters: username (string, required), email (string, required), age (optional int)
```

### Test Commands

#### CLI Test
```bash
python -m backend.cli \
  --url http://127.0.0.1:8001/api/typed \
  --method POST \
  --time 30
```

#### HTTP Service Test
```bash
# Start inference service
python backend/server.py

# Run inference via HTTP
curl -X POST -H "Content-Type: application/json" \
  -d '{"url":"http://127.0.0.1:8001/api/typed","method":"POST","time":30}' \
  http://127.0.0.1:8000/infer
```

#### Spec Generation Test
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"url":"http://127.0.0.1:8001/api/typed","method":"POST","time":30}' \
  http://127.0.0.1:8000/spec
```

### Expected Output

#### CLI Output
```json
{
  "url": "http://127.0.0.1:8001/api/typed",
  "method": "POST",
  "parameters": [
    {
      "name": "username",
      "location": "body",
      "required": true,
      "type": "string",
      "nullable": false,
      "confidence": 0.85,
      "evidence": [
        {
          "source": "error_probe",
          "detail": "Structured validation error"
        },
        {
          "source": "type_probe", 
          "detail": "Type inferred: string"
        }
      ]
    },
    {
      "name": "email",
      "location": "body", 
      "required": true,
      "type": "string",
      "nullable": false,
      "confidence": 0.82,
      "evidence": [
        {
          "source": "error_probe",
          "detail": "Multiple parameter references"
        },
        {
          "source": "type_probe",
          "detail": "Type inferred: string"
        }
      ]
    }
  ],
  "meta": {
    "total_parameters": 2,
    "partial_failures": 0,
    "execution_time_ms": 2500,
    "error_probe_time_ms": 800,
    "type_inference_time_ms": 1200,
    "time_limit_seconds": 30
  }
}
```

#### HTTP Service Response
- **Status**: 200 OK
- **Time**: ~2.5 seconds
- **Parameters**: 2 discovered with high confidence (>0.8)
- **No failures**: All probes succeeded

#### Generated Spec
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Inferred API Spec",
    "version": "0.1.0",
    "description": "Generated via automated parameter inference"
  },
  "paths": {
    "/api/typed": {
      "post": {
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "username": {
                    "type": "string",
                    "x-confidence": 0.85,
                    "required": true
                  },
                  "email": {
                    "type": "string", 
                    "x-confidence": 0.82,
                    "required": true
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

### Success Criteria
- ✅ All required parameters discovered
- ✅ High confidence scores (>0.8)
- ✅ Correct type inference (string)
- ✅ Proper location detection (body)
- ✅ No partial failures
- ✅ Execution within time limit
- ✅ Valid OpenAPI spec generated

---

## Test Case 2: Medium Case - Partial Discovery

### Description
Tests against an endpoint with mixed parameter types and some validation ambiguity.

### Test Setup
```python
# Target endpoint: http://127.0.0.1:8002/api/secure
# Expected parameters: username (string, required), preferences (optional dict)
# Challenge: preferences parameter may not be discoverable via type inference
```

### Test Commands

#### CLI Test
```bash
python -m backend.cli \
  --url http://127.0.0.1:8002/api/secure \
  --method POST \
  --time 20
```

#### HTTP Service Test
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"url":"http://127.0.0.1:8002/api/secure","method":"POST","time":20}' \
  http://127.0.0.1:8000/infer
```

### Expected Output

#### CLI Output
```json
{
  "url": "http://127.0.0.1:8002/api/secure",
  "method": "POST",
  "parameters": [
    {
      "name": "username",
      "location": "body",
      "required": true,
      "type": "string",
      "nullable": false,
      "confidence": 0.72,
      "evidence": [
        {
          "source": "error_probe",
          "detail": "Structured validation error"
        }
      ]
    },
    {
      "name": "preferences",
      "location": "body",
      "required": false,
      "type": "unknown",
      "nullable": false,
      "confidence": 0.45,
      "evidence": [
        {
          "source": "error_probe",
          "detail": "Generic error patterns"
        }
      ]
    }
  ],
  "meta": {
    "total_parameters": 2,
    "partial_failures": 1,
    "execution_time_ms": 18000,
    "error_probe_time_ms": 500,
    "type_inference_time_ms": 15000,
    "time_limit_seconds": 20
  }
}
```

#### HTTP Service Response
- **Status**: 200 OK
- **Time**: ~18 seconds (time limit reached)
- **Parameters**: 2 discovered, 1 with low confidence
- **Partial failure**: Type inference failed for preferences parameter

### Success Criteria
- ✅ Some parameters discovered
- ✅ Mixed confidence scores (0.45-0.72)
- ✅ Partial type inference success
- ✅ Time limit respected
- ⚠️ Some partial failures expected

---

## Test Case 3: Worst Case - Hostile/Unresponsive Endpoint

### Description
Tests against an endpoint that returns generic errors, timeouts, or has no discoverable parameters.

### Test Setup
```python
# Target endpoint: http://127.0.0.1:8003/api/generic
# Expected behavior: Always returns "bad request" with no parameter details
# Challenge: No structured errors to analyze
```

### Test Commands

#### CLI Test
```bash
python -m backend.cli \
  --url http://127.0.0.1:8003/api/generic \
  --method POST \
  --time 10
```

#### HTTP Service Test
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"url":"http://127.0.0.1:8003/api/generic","method":"POST","time":10}' \
  http://127.0.0.1:8000/infer
```

### Expected Output

#### CLI Output
```json
{
  "url": "http://127.0.0.1:8003/api/generic",
  "method": "POST",
  "parameters": [],
  "meta": {
    "total_parameters": 0,
    "partial_failures": 0,
    "execution_time_ms": 10000,
    "error_probe_time_ms": 10000,
    "type_inference_time_ms": 0,
    "time_limit_seconds": 10
  }
}
```

#### HTTP Service Response
- **Status**: 200 OK
- **Time**: ~10 seconds (full timeout)
- **Parameters**: 0 discovered
- **No failures**: Graceful handling of unresponsive endpoint

#### Generated Spec
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Inferred API Spec",
    "version": "0.1.0",
    "description": "Generated via automated parameter inference",
    "x-inference-meta": {
      "total_parameters": 0,
      "partial_failures": 0,
      "execution_time_ms": 10000
    }
  },
  "paths": {},
  "servers": [
    {
      "url": "http://127.0.0.1:8003",
      "description": "Inferred API server"
    }
  ]
}
```

### Success Criteria
- ✅ No parameters discovered (expected for hostile endpoint)
- ✅ No crashes or unhandled exceptions
- ✅ Time limits respected
- ✅ Graceful degradation to empty results
- ✅ Valid but empty OpenAPI spec generated

---

## Test Execution Instructions

### Prerequisites
1. Start all test servers on different ports:
   ```bash
   # Terminal 1
   python backend/test_app.py --port 8001
   
   # Terminal 2  
   python backend/error_test_app.py --port 8002
   
   # Terminal 3
   python backend/generic_test_app.py --port 8003
   ```

2. Start inference service:
   ```bash
   python backend/server.py
   ```

3. Run tests in order:
   ```bash
   # Test 1 (Best Case)
   python -m backend.cli --url http://127.0.0.1:8001/api/typed --method POST --time 30
   
   # Test 2 (Medium Case)  
   python -m backend.cli --url http://127.0.0.1:8002/api/secure --method POST --time 20
   
   # Test 3 (Worst Case)
   python -m backend.cli --url http://127.0.0.1:8003/api/generic --method POST --time 10
   ```

### Expected Results Summary

| Test Case | Parameters Found | Confidence Range | Failures | Execution Time | Status |
|-----------|-----------------|------------------|----------|----------------|--------|
| Best Case | 2-3 parameters | 0.8-0.9 | 0 | Fast (2-5s) | ✅ Success |
| Medium Case | 1-2 parameters | 0.4-0.7 | 1 | Medium (10-20s) | ⚠️ Partial |
| Worst Case | 0 parameters | 0.0-0.1 | 0 | Timeout (10s) | ✅ Graceful |

### Key Validation Points

1. **Parameter Discovery**: Error probe should find parameters in best/medium cases
2. **Type Inference**: Should work for discoverable parameters, fail gracefully for others
3. **Confidence Scoring**: High confidence for clear evidence, low for generic errors
4. **Time Management**: Respect limits, stop early when appropriate
5. **Error Handling**: No crashes, always return valid JSON structure
6. **Spec Generation**: Valid OpenAPI output even with empty results

### Edge Cases to Verify

- **Network timeouts**: Ensure graceful handling
- **Malformed URLs**: Proper validation and error responses
- **Invalid methods**: Clear error messages for unsupported HTTP methods
- **Empty responses**: Handle APIs that return nothing
- **Rate limiting**: Respect time limits even under pressure
- **Memory efficiency**: No memory leaks during long-running inferences

This comprehensive test suite validates the entire APISec pipeline from optimal to hostile conditions.
