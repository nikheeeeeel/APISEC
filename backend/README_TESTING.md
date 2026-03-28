# APISEC Testing Guide

This document provides comprehensive information about the testing infrastructure implemented for the APISEC project.

## Overview

The APISEC project now includes a complete testing framework covering:
- **Unit Testing**: Individual component testing
- **Integration Testing**: Component interaction testing  
- **Functional Testing**: End-to-end workflow testing
- **Load Testing**: Performance and stress testing
- **E2E Testing**: Frontend-backend integration testing

## Testing Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── unit/                          # Unit tests
│   ├── test_api_endpoints.py     # FastAPI endpoint tests
│   ├── test_schema_monitor.py    # Schema monitoring tests
│   ├── test_registry_db.py       # Database operations tests
│   ├── test_runtime_validator.py # Runtime validation tests
│   ├── test_enhanced_validator.py # Enhanced validator tests
│   └── test_schema_diffing.py    # Schema diffing tests
├── integration/                   # Integration tests
│   └── test_api_workflows.py     # Complete workflow tests
├── functional/                    # Functional tests
│   └── test_user_workflows.py    # User journey tests
├── load/                          # Load testing
│   ├── locustfile.py             # Locust load testing
│   └── performance_tests.py      # Performance benchmarking
├── e2e/                          # End-to-end tests
│   └── test_frontend_integration.py # Frontend integration
└── fixtures/                      # Test data
    ├── sample_schemas/           # Sample API schemas
    └── mock_responses/           # Mock API responses
```

## Running Tests

### Prerequisites

```bash
# Install testing dependencies
cd backend
pip install -r requirements.txt
```

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ -v --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_api_endpoints.py -v

# Run tests by marker
pytest -m unit -v
```

### Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific integration test
pytest tests/integration/test_api_workflows.py -v
```

### Functional Tests

```bash
# Run all functional tests
pytest tests/functional/ -v

# Run specific functional test
pytest tests/functional/test_user_workflows.py -v
```

### Load Testing

#### Using Locust

```bash
# Start Locust web interface
cd backend
locust -f tests/load/locustfile.py --host http://localhost:8000

# Run headless load test
locust -f tests/load/locustfile.py --headless --users 50 --spawn-rate 5 --run-time 300s --host http://localhost:8000
```

#### Using Performance Tests

```bash
# Run quick performance test
cd backend
python tests/load/performance_tests.py http://localhost:8000 quick

# Run comprehensive benchmark
python tests/load/performance_tests.py http://localhost:8000 comprehensive

# Run stress test
python tests/load/performance_tests.py http://localhost:8000 stress 60
```

### End-to-End Tests

```bash
# Install Playwright browsers
cd backend
playwright install chromium

# Run E2E tests
pytest tests/e2e/ -v --browser chromium

# Run E2E tests directly
python tests/e2e/test_frontend_integration.py
```

## Test Configuration

### pytest.ini

The `pytest.ini` file configures:
- Test discovery patterns
- Coverage reporting
- Custom markers
- Async testing support
- Timeout settings

### Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # Tests requiring external services
@pytest.mark.functional    # End-to-end workflow tests
@pytest.mark.load          # Performance/load tests
@pytest.mark.slow          # Tests taking > 1 second
@pytest.mark.external      # Tests requiring internet
@pytest.mark.database      # Tests requiring database
```

### Fixtures

Key fixtures available in `conftest.py`:

- `test_client`: FastAPI test client with temporary database
- `sample_openapi_schema`: Sample OpenAPI 3.0 schema
- `sample_swagger_schema`: Sample Swagger 2.0 schema
- `mock_http_client`: Mock HTTP client for external API calls
- `test_database`: Temporary SQLite database for testing

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) includes:

### Jobs

1. **backend-tests**: Unit, integration, and functional tests
2. **frontend-tests**: ESLint and build verification
3. **load-tests**: Performance testing (main branch only)
4. **security-scan**: Trivy and CodeQL security scanning
5. **docker-tests**: Docker container testing
6. **e2e-tests**: Frontend-backend integration tests
7. **performance-regression**: Performance regression detection
8. **deploy-staging**: Deploy to staging environment
9. **deploy-production**: Deploy to production environment

### Triggers

- Push to `main` or `develop` branches
- Pull requests to `main`
- Manual workflow dispatch

### Quality Gates

- **Coverage**: Minimum 80% test coverage
- **Performance**: No more than 10% performance regression
- **Security**: No high-severity vulnerabilities
- **Tests**: All tests must pass

## Test Data

### Sample Schemas

Located in `tests/fixtures/sample_schemas/`:

- `petstore_openapi.json`: Complete Petstore API (OpenAPI 3.0)
- `simple_api.json`: Simple user management API

### Mock Responses

Use the mock fixtures for consistent testing:

```python
def test_with_mock(mock_http_client, sample_api_responses):
    mock_http_client.get.return_value = Mock(
        status_code=200,
        json=sample_api_responses["users_list"]
    )
    # Test implementation
```

## Performance Testing

### Metrics Tracked

- **Response Time**: Average, min, max, P95, P99
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests
- **Concurrency**: Number of simultaneous users

### Load Testing Scenarios

1. **Normal Load**: 10 concurrent users, typical usage patterns
2. **Peak Load**: 50 concurrent users, stress testing
3. **Burst Load**: Rapid traffic spikes
4. **Sustained Load**: Extended duration testing

### Performance Benchmarks

- Health check: < 50ms average response time
- API listing: < 200ms average response time
- Schema discovery: < 5s average response time
- Runtime validation: < 10s average response time

## Best Practices

### Writing Tests

1. **Use descriptive test names**: `test_user_creates_api_successfully`
2. **Arrange-Act-Assert pattern**: Clear test structure
3. **Use fixtures**: Reuse test setup and data
4. **Mock external dependencies**: Ensure test isolation
5. **Test edge cases**: Not just happy paths

### Test Organization

1. **Unit tests**: Test individual functions/methods
2. **Integration tests**: Test component interactions
3. **Functional tests**: Test complete user workflows
4. **Load tests**: Test performance under load

### CI/CD Integration

1. **Fast feedback**: Run unit tests first
2. **Parallel execution**: Run test types in parallel
3. **Fail fast**: Stop pipeline on first failure
4. **Artifact retention**: Keep test results and reports

## Troubleshooting

### Common Issues

1. **Database errors**: Ensure test database is properly isolated
2. **Port conflicts**: Use different ports for concurrent tests
3. **Timeout errors**: Increase timeout values for slow tests
4. **Import errors**: Check Python path and module imports

### Debugging Tests

```bash
# Run with verbose output
pytest tests/unit/test_api_endpoints.py -v -s

# Run with debugger
pytest tests/unit/test_api_endpoints.py --pdb

# Run specific test method
pytest tests/unit/test_api_endpoints.py::TestHealthEndpoint::test_health_check -v
```

### Performance Issues

1. **Check resource usage**: Monitor CPU and memory
2. **Profile tests**: Use Python profiling tools
3. **Optimize fixtures**: Reduce setup/teardown time
4. **Parallel execution**: Use pytest-xdist for parallel testing

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_<feature>_<scenario>`
2. **Add appropriate markers**: Use pytest markers correctly
3. **Update fixtures**: Add new test data if needed
4. **Document complex tests**: Add comments for clarity
5. **Update CI/CD**: Add new test types to pipeline if needed

## Reports and Artifacts

### Coverage Reports

- HTML reports: `backend/htmlcov/index.html`
- XML reports: `backend/coverage.xml`
- Coverage badges: Generated automatically

### Load Test Reports

- Locust HTML reports: `backend/load-test-report.html`
- Performance benchmarks: `backend/benchmark_results_*.json`

### Test Results

- JUnit XML: For CI/CD integration
- Test artifacts: Stored in GitHub Actions artifacts
- Coverage data: Uploaded to Codecov

This comprehensive testing infrastructure ensures the APISEC application maintains high quality, performance, and reliability throughout development and deployment.
