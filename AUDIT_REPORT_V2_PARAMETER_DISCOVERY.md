# REST Parameter Discovery v2 — Audit Report

**Date:** February 15, 2025  
**Scope:** v2 REST parameter discovery pipeline health assessment  
**Methodology:** Static analysis, dependency mapping, execution-path tracing. No refactoring performed.

---

## 1. Repository Structure Overview

### 1.1 Directory Layout

```
backend/
├── classification/      # Endpoint classification (v2)
├── fingerprint/         # Response fingerprinting, framework detection
├── inference/           # v1 inference (error probe, type probe, etc.)
├── models/              # DiscoveryRequest, DiscoveryContext, ProbeResult
├── orchestrator/        # v2_orchestrator, discovery_orchestrator (v1)
├── probes/              # Differential engine, strategies, location resolver
├── scoring/             # Confidence scoring, framework signals
├── spec/                # Spec generation
├── transport/           # HTTP clients (requests-based)
├── validation/          # rest_v2_release, integration tests
└── tests/               # Unit tests
```

### 1.2 v2 Pipeline Entry Points

- **Primary:** `orchestrator.v2_orchestrator.V2Orchestrator.discover_parameters()`
- **Factory:** `create_v2_orchestrator()`, `orchestrate_inference_v2()`

---

## 2. Module Dependency Map

### 2.1 Dependency Graph (Key v2 Paths)

```
V2Orchestrator
  ├── models (DiscoveryRequest, DiscoveryContext)
  ├── transport (RequestsTransportClient, TransportClientInterface)
  ├── probes (ProbeFactory)
  ├── fingerprint (ResponseFingerprint, create_fingerprint)
  ├── probes.differential_engine (DifferentialEngine)
  ├── probes.location_resolver (LocationResolver)
  ├── scoring.confidence_scoring (WeightedConfidenceScorer)
  └── classification.endpoint_classifier (EnhancedEndpointClassifier)

DifferentialEngine
  ├── models (DiscoveryRequest, DiscoveryContext, ProbeResult)
  ├── transport (TransportClientInterface)
  ├── fingerprint (create_fingerprint, compare_fingerprints, extract_error_patterns_from_fingerprint)
  └── probes.strategies (ProbeStrategy, StringProbe, NumericProbe, BooleanProbe)

EndpointClassifier
  ├── models (DiscoveryRequest, DiscoveryContext)
  ├── transport (TransportClientInterface)
  ├── fingerprint (ResponseFingerprint)
  ├── scoring.framework_signals (FrameworkSignal, FrameworkSignalDetector)
  └── probes.differential_engine (ParameterCandidate)
```

### 2.2 Circular Imports

- **None found** in the v2 path. The `rest_v2_release.py` circular-dependency check is heuristic-based (checks if module name appears in file content) and can produce false positives/negatives.

### 2.3 Tight Coupling

| Location | Coupling Issue |
|----------|----------------|
| `v2_orchestrator` | Hardcodes `RequestsTransportClient`, `ProbeFactory`, specific probe strategies. No injection for transport or probe selection. |
| `v2_orchestrator` | Directly accesses `self.endpoint_classifier.framework_detector` before `endpoint_classifier` exists (construction-order bug). |
| `DifferentialEngine` | Tightly coupled to `ProbeStrategy` implementations; no abstraction for candidate-name generation. |
| `location_resolver` | Assumes `ParameterCandidate` structure; v2 orchestrator passes `ProbeResult` (different shape). |
| `transport.client` | `_prepare_headers` uses `location` but it is not in its signature (NameError risk). |

---

## 3. Code Quality Issues

### 3.1 Mutable Default Arguments

| File | Location | Issue |
|------|----------|-------|
| `rest_v2_release.py` | `ValidationConfig` L41–42, `ReleaseValidatorConfig` L50–56 | `performance_targets=None`, `real_world_endpoints=None`, `confidence_thresholds=None` — mutated in `__post_init__` with `self.x = {}` or `[]`. Not classic mutable-default bug but mutable instance defaults. |
| `ValidationConfig` | L41–42 | Same pattern. |

**Note:** No `def f(x=[])`-style mutable defaults found in function signatures.

### 3.2 Direct Network Calls in Core Logic

| File | Function | Issue |
|------|----------|-------|
| `inference/error_probe.py` | `infer_parameters` | Direct `requests.post`, `requests.get`. |
| `inference/type_probe.py` | `infer_parameter_type` | Direct `requests.post`, `requests.get`. |
| `inference/binary_probe.py` | `infer_file_parameters` | Direct `requests.post`. |
| `inference/content_type_probe.py` | `detect_content_type` | Direct `requests.post`. |
| `inference/location_probe.py` | `infer_parameter_location` | Direct `requests.get/post`. |
| `inference/classifier.py` | `classify_endpoint` | Direct `requests.get/post`. |

**v2 path:** Transport is abstracted via `TransportClientInterface`. Differential engine, scoring, and fingerprinting do not perform network calls directly.

### 3.3 Global State Usage

| Location | Issue |
|----------|-------|
| `v2_orchestrator.OrchestratorConfig` | `os.getenv('ENABLE_REST_V2', 'true')` read at class definition time — not at runtime. |
| `rest_v2_release.ReleaseValidatorConfig` | No global mutable state. |

### 3.4 Missing Type Hints

- `transport/client.py`: `_prepare_headers` — `location` used but not passed; return type missing.
- `endpoint_classifier.py`: Several helpers (`_extract_content_type_from_response`, etc.) lack return types.
- `confidence_scoring.py`: `calculate_simple_confidence` — `ParameterConfidence` return type present but `metadata` argument typing incomplete.
- `location_resolver.py`: `_test_body_location`, etc. — `response` parameters untyped.

---

## 4. Test Execution Report

### 4.1 Blocking Issue

**SyntaxError in `probes/strategies.py` L475–478:**

```text
SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' on line 476
```

`_generate_nested_objects` has unbalanced braces in the second list element:

```python
{param_name: {"data": {"items": [{"id": 1}, {"id": 2}]}},  # Missing '}' before comma
```

### 4.2 Test Collection Result

- **0 tests collected** due to the syntax error (probes imported transitively by tests).
- **Failing tests:** Cannot be run until the syntax error is fixed.
- **Flaky behavior:** Unknown; tests not executed.
- **Zero-parameter discovery tests:** `test_differential_engine.py` contains tests for empty results and error handling but they cannot run.

### 4.3 Pydantic Deprecation Warnings

- `@validator` → should migrate to `@field_validator`.
- `class Config` → should migrate to `ConfigDict`.

---

## 5. Parameter Discovery Pipeline — Zero-Parameter Trace

### 5.1 Execution Path When URI Returns 0 Parameters

1. `V2Orchestrator.discover_parameters(request)`
2. Phase 1: `_capture_baseline_fingerprint(request)` → `ResponseFingerprint`
3. Phase 2: `differential_engine.run(request)` → `List[ProbeResult]` (or `List[ParameterCandidate]` depending on code path)
4. Phase 3: Iterate candidates → `location_resolver.resolve_location()`
5. Phase 4: `framework_detector.detect_signals()`
6. Phase 5: Confidence scoring
7. Phase 6: Endpoint classification
8. Phase 7: Result assembly

### 5.2 Identified Failure Points

| # | Failure Point | Component | Root Cause |
|---|---------------|-----------|------------|
| 1 | **Candidate generation always empty** | Parsing | `_generate_candidate_names()` uses `baseline_fingerprint.body_hash` (SHA256 hex) in regex. Patterns like `parameter\s*['\"]([^'\"]+)['\"]` search a hash, not the response body, so matches never occur. |
| 2 | **V2Orchestrator construction crashes** | Orchestration | `create_enhanced_classifier(..., framework_detector=self.endpoint_classifier.framework_detector)` references `endpoint_classifier` before it is created. |
| 3 | **ProbeResult vs ParameterCandidate** | Type mismatch | `differential_engine.run()` returns `ProbeResult` with `parameter_name`, `diffs`, `evidence`, etc. Orchestrator and `location_resolver` expect `ParameterCandidate` with `name`. `candidate.name` will fail on `ProbeResult`. |
| 4 | **ProbeResult constructor mismatch** | Differential engine | Local `ProbeResult` dataclass expects `(parameter_name, diffs, provisional_score, evidence, sources, metadata)`. Code passes `success`, `parameters` (from models.ProbeResult). Constructor mismatch. |
| 5 | **FrameworkSignalDetector.detect_signals() signature** | Framework signals | Called as `detect_signals(request, baseline_fingerprint.body_hash)`. Signature is `(response_text, response_headers, status_code, response_body)`. Wrong arity and types; `body_hash` is not the body. |
| 6 | **ResponseFingerprint vs HTTP Response** | Endpoint classifier | `initial_response` is a `ResponseFingerprint` but code uses `.status_code` and `.text`. Fingerprint has `.status` and `.body_hash`, not `.text`. |
| 7 | **_prepare_headers uses undefined `location`** | Transport | `transport/client.py` L99–100: `elif location == "body"` — `location` not in `_prepare_headers` signature. Likely `NameError`. |
| 8 | **location_resolver.resolve_location signature** | Probes | Definition: `resolve_location(self, parameter_name, candidate, request)` — missing comma between `candidate` and `request` in some call paths. |
| 9 | **JavaScript literals in Python** | Probes | `probes/strategies.py` L379, L389, L406: `true`, `false`, `null` used in arrays. Python expects `True`, `False`, `None`. Causes `NameError`. |
| 10 | **Result assembly dict comprehensions** | Orchestrator | L204–210: `'location_resolution'` and `'confidence_scoring'` comprehensions reference `candidate`, `location_result`, `name`, `info` incorrectly; will raise or produce wrong structure. |

### 5.3 Failure Classification

| Category | Failures |
|----------|----------|
| **Transport** | #7 (`location` NameError) |
| **Parsing** | #1 (candidate generation from body_hash) |
| **Scoring** | Indirect — no candidates to score |
| **Validation** | #4 (ProbeResult constructor) |
| **Orchestration / Type mismatch** | #2, #3, #5, #6, #8, #10 |
| **Language errors** | #9 (JS vs Python) |

---

## 6. Bug List (Concise)

| ID | Severity | Location | Description |
|----|----------|----------|-------------|
| B1 | Critical | `probes/strategies.py` L476 | SyntaxError: unbalanced `{` in nested object literal. |
| B2 | Critical | `probes/strategies.py` L379, 389, 406 | `true`/`false`/`null` used instead of `True`/`False`/`None`. |
| B3 | Critical | `probes/differential_engine.py` L168 | `body_hash` used for regex; must use raw body for parameter extraction. |
| B4 | Critical | `orchestrator/v2_orchestrator.py` L61 | References `self.endpoint_classifier` before it exists. |
| B5 | Critical | `orchestrator/v2_orchestrator.py` L106–113 | Expects `candidate.name`; `ProbeResult` has `parameter_name`. |
| B6 | Critical | `probes/differential_engine.py` L245–271 | `ProbeResult` constructor args don’t match dataclass definition. |
| B7 | Critical | `classification/endpoint_classifier.py` L115–117, 126 | Uses `initial_response.status_code`, `.text` on `ResponseFingerprint` (has `.status`, `.body_hash`). |
| B8 | Critical | `orchestrator/v2_orchestrator.py` L119–121 | `detect_signals(request, body_hash)` — wrong signature and data. |
| B9 | High | `transport/client.py` L99–100 | `location` used in `_prepare_headers` but not passed in. |
| B10 | High | `probes/location_resolver.py` L78 | Missing comma in `resolve_location(parameter_name, candidate, request)`. |
| B11 | High | `classification/endpoint_classifier.py` L375–376 | Uses `signals.auth_indicators`, `signals.error_indicators` (not in `ClassificationSignals`). |
| B12 | High | `classification/endpoint_classifier.py` L177 | Missing comma in metadata dict. |
| B13 | Medium | `scoring/confidence_scoring.py` L391 | `normalized_score = min(max(base_score, 1.0), 0.0)` — always 0.0. |
| B14 | Medium | `scoring/confidence_scoring.py` L262–268 | `location_tests` as dicts; code uses `test.success`, `test.location` (attribute access). |

---

## 7. Architectural Weaknesses

1. **No shared response model** — `ResponseFingerprint` vs raw HTTP response used inconsistently (classifier, framework detector).
2. **ProbeResult vs ParameterCandidate split** — Two similar concepts with different fields; orchestration assumes one, engine returns the other.
3. **Candidate generation depends on error text** — Only derives names from error messages; no body parsing, no schema hints.
4. **Fingerprint loses body content** — `create_fingerprint` hashes the body; candidate extraction needs raw body.
5. **Mixed v1/v2 surface** — `FrameworkDetector` (fingerprint) vs `FrameworkSignalDetector` (scoring); different APIs and roles.
6. **ValidationConfig mutable defaults** — `performance_targets=None` etc. mutated in `__post_init__`; easy to misuse.
7. **Environment read at import time** — `OrchestratorConfig.enable_v2` reads `ENABLE_REST_V2` at class definition time.
8. **No interface for candidate generation** — Heuristic is hardcoded in differential engine; not pluggable.

---

## 8. Priority Order of Fixes

### P0 — Unblock execution

1. **B1** — Fix syntax error in `probes/strategies.py` (line 476).
2. **B2** — Replace `true`/`false`/`null` with `True`/`False`/`None` in `probes/strategies.py`.
3. **B4** — Fix `V2Orchestrator` constructor so `endpoint_classifier` is created before use (or inject `framework_detector` separately).
4. **B9** — Add `location` parameter to `_prepare_headers` or remove its use.

### P1 — Zero-parameter discovery

5. **B3** — Use raw response body (not `body_hash`) for candidate-name extraction, or extend fingerprint to retain body for parsing.
6. **B5** — Align orchestrator and differential engine types: either return `ParameterCandidate` from engine or adapt orchestration to `ProbeResult`.
7. **B6** — Make `ProbeResult` construction match the dataclass (or unify with models.ProbeResult).
8. **B7** — Pass actual HTTP response (or a common response-like object) to classifier instead of `ResponseFingerprint`; or add `.status_code`/`.text` compatibility.
9. **B8** — Call `detect_signals` with `(response_text, response_headers, status_code, response_body)` and pass real response data.

### P2 — Correctness and robustness

10. **B10** — Fix `location_resolver.resolve_location` signature (add comma).
11. **B11** — Use `pattern_evidence` in `_determine_endpoint_type` instead of non-existent `signals.auth_indicators` etc.
12. **B12** — Fix metadata dict syntax (missing comma).
13. **B13** — Fix confidence normalization in `calculate_simple_confidence`.
14. **B14** — Normalize `location_tests` to objects with `.success`/`.location`, or use dict access in scorer.

### P3 — Code quality

15. Resolve Pydantic deprecations (validators, config).
16. Add type hints to transport, classifier, and scoring helpers.
17. Replace mutable default patterns in validation configs.

---

## 9. Summary

The v2 REST parameter discovery pipeline is **not functional** in its current state:

- A **syntax error** prevents any test or import from succeeding.
- **Candidate generation** fails because regex is run on `body_hash` instead of the response body.
- **Constructor and type mismatches** cause crashes before scoring or validation.
- **API mismatches** between fingerprint, classifier, and framework detector block end-to-end flow.

Fixes should follow the P0 → P1 → P2 order to first make the pipeline run, then produce correct zero-parameter behavior, and finally improve correctness and maintainability.
