#!/usr/bin/env python3
"""
Performance testing utilities and benchmarks for APISEC.
"""

import time
import asyncio
import statistics
import json
from typing import Dict, List, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import aiohttp
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PerformanceMetrics:
    """Performance metrics data class."""
    operation: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    total_duration: float


class PerformanceTester:
    """Performance testing utility for APISEC endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        # Set reasonable timeouts
        self.session.timeout = 30
    
    def benchmark_endpoint(self, endpoint: str, method: str = "GET", 
                          data: Dict = None, params: Dict = None,
                          num_requests: int = 100, concurrent_users: int = 10) -> PerformanceMetrics:
        """Benchmark a specific endpoint."""
        
        url = f"{self.base_url}{endpoint}"
        response_times = []
        successful_requests = 0
        failed_requests = 0
        errors = []
        
        start_time = time.time()
        
        def make_request():
            """Make a single request and return response time and success."""
            nonlocal successful_requests, failed_requests
            request_start = time.time()
            
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, params=params)
                elif method.upper() == "POST":
                    if data:
                        if isinstance(data, dict):
                            response = self.session.post(url, json=data, params=params)
                        else:
                            response = self.session.post(url, data=data, params=params)
                    else:
                        response = self.session.post(url, params=params)
                elif method.upper() == "PUT":
                    response = self.session.put(url, json=data, params=params)
                elif method.upper() == "DELETE":
                    response = self.session.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                request_time = time.time() - request_start
                
                if response.status_code < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    errors.append(f"HTTP {response.status_code}: {response.text[:100]}")
                
                return request_time, response.status_code
                
            except Exception as e:
                failed_requests += 1
                errors.append(str(e))
                return time.time() - request_start, 0
        
        # Execute requests concurrently
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            
            for future in as_completed(futures):
                request_time, status_code = future.result()
                response_times.append(request_time)
        
        total_duration = time.time() - start_time
        
        # Calculate metrics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_response_time = sorted_times[int(0.95 * len(sorted_times))]
            p99_response_time = sorted_times[int(0.99 * len(sorted_times))]
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        requests_per_second = num_requests / total_duration if total_duration > 0 else 0
        error_rate = (failed_requests / num_requests * 100) if num_requests > 0 else 0
        
        return PerformanceMetrics(
            operation=f"{method} {endpoint}",
            total_requests=num_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            total_duration=total_duration
        )
    
    async def benchmark_endpoint_async(self, endpoint: str, method: str = "GET",
                                      data: Dict = None, params: Dict = None,
                                      num_requests: int = 100, concurrent_users: int = 10) -> PerformanceMetrics:
        """Benchmark endpoint using async requests."""
        
        url = f"{self.base_url}{endpoint}"
        response_times = []
        successful_requests = 0
        failed_requests = 0
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async def make_request():
                nonlocal successful_requests, failed_requests
                request_start = time.time()
                
                try:
                    if method.upper() == "GET":
                        async with session.get(url, params=params) as response:
                            await response.text()
                            request_time = time.time() - request_start
                            
                            if response.status < 400:
                                successful_requests += 1
                            else:
                                failed_requests += 1
                            
                            return request_time, response.status
                    
                    elif method.upper() == "POST":
                        if data:
                            async with session.post(url, json=data, params=params) as response:
                                await response.text()
                                request_time = time.time() - request_start
                                
                                if response.status < 400:
                                    successful_requests += 1
                                else:
                                    failed_requests += 1
                                
                                return request_time, response.status
                        else:
                            async with session.post(url, params=params) as response:
                                await response.text()
                                request_time = time.time() - request_start
                                
                                if response.status < 400:
                                    successful_requests += 1
                                else:
                                    failed_requests += 1
                                
                                return request_time, response.status
                
                except Exception:
                    failed_requests += 1
                    return time.time() - request_start, 0
            
            # Execute requests concurrently
            tasks = [make_request() for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            for request_time, status_code in results:
                response_times.append(request_time)
        
        total_duration = time.time() - start_time
        
        # Calculate metrics (same as sync version)
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            sorted_times = sorted(response_times)
            p95_response_time = sorted_times[int(0.95 * len(sorted_times))]
            p99_response_time = sorted_times[int(0.99 * len(sorted_times))]
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        requests_per_second = num_requests / total_duration if total_duration > 0 else 0
        error_rate = (failed_requests / num_requests * 100) if num_requests > 0 else 0
        
        return PerformanceMetrics(
            operation=f"{method} {endpoint} (async)",
            total_requests=num_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            total_duration=total_duration
        )
    
    def run_comprehensive_benchmark(self) -> Dict[str, PerformanceMetrics]:
        """Run comprehensive benchmark of all major endpoints."""
        
        benchmarks = {}
        
        # Health check (should be fastest)
        print("Benchmarking health check...")
        benchmarks["health_check"] = self.benchmark_endpoint(
            "/health", num_requests=1000, concurrent_users=50
        )
        
        # Get all APIs
        print("Benchmarking get all APIs...")
        benchmarks["get_all_apis"] = self.benchmark_endpoint(
            "/api/apis", num_requests=500, concurrent_users=25
        )
        
        # Create API
        print("Benchmarking create API...")
        benchmarks["create_api"] = self.benchmark_endpoint(
            "/api/apis", method="POST", 
            data={
                "name": "Benchmark API",
                "base_url": "https://benchmark.example.com",
                "description": "API created during benchmarking"
            },
            num_requests=100, concurrent_users=10
        )
        
        # Schema discovery
        print("Benchmarking schema discovery...")
        benchmarks["discover_schema"] = self.benchmark_endpoint(
            "/discover-schema", method="POST",
            data={"url": "https://jsonplaceholder.typicode.com"},
            num_requests=200, concurrent_users=15
        )
        
        # Runtime validation
        print("Benchmarking runtime validation...")
        sample_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        benchmarks["runtime_validation"] = self.benchmark_endpoint(
            "/validate-runtime", method="POST",
            data={
                "base_url": "https://jsonplaceholder.typicode.com",
                "schema_info": sample_schema
            },
            num_requests=100, concurrent_users=10
        )
        
        return benchmarks
    
    def generate_performance_report(self, benchmarks: Dict[str, PerformanceMetrics]) -> str:
        """Generate a performance report from benchmarks."""
        
        report = []
        report.append("# APISEC Performance Report")
        report.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Base URL: {self.base_url}")
        report.append("")
        
        # Summary table
        report.append("## Performance Summary")
        report.append("")
        report.append("| Operation | Requests/sec | Avg Response (ms) | P95 (ms) | P99 (ms) | Error Rate (%) |")
        report.append("|-----------|-------------|------------------|----------|----------|----------------|")
        
        for name, metrics in benchmarks.items():
            report.append(f"| {metrics.operation} | "
                         f"{metrics.requests_per_second:.2f} | "
                         f"{metrics.avg_response_time*1000:.2f} | "
                         f"{metrics.p95_response_time*1000:.2f} | "
                         f"{metrics.p99_response_time*1000:.2f} | "
                         f"{metrics.error_rate:.2f} |")
        
        report.append("")
        
        # Detailed metrics
        report.append("## Detailed Metrics")
        report.append("")
        
        for name, metrics in benchmarks.items():
            report.append(f"### {metrics.operation}")
            report.append(f"- **Total Requests**: {metrics.total_requests}")
            report.append(f"- **Successful**: {metrics.successful_requests}")
            report.append(f"- **Failed**: {metrics.failed_requests}")
            report.append(f"- **Success Rate**: {100 - metrics.error_rate:.2f}%")
            report.append(f"- **Average Response Time**: {metrics.avg_response_time*1000:.2f} ms")
            report.append(f"- **Min Response Time**: {metrics.min_response_time*1000:.2f} ms")
            report.append(f"- **Max Response Time**: {metrics.max_response_time*1000:.2f} ms")
            report.append(f"- **95th Percentile**: {metrics.p95_response_time*1000:.2f} ms")
            report.append(f"- **99th Percentile**: {metrics.p99_response_time*1000:.2f} ms")
            report.append(f"- **Requests per Second**: {metrics.requests_per_second:.2f}")
            report.append(f"- **Total Duration**: {metrics.total_duration:.2f} seconds")
            report.append("")
        
        # Performance recommendations
        report.append("## Performance Recommendations")
        report.append("")
        
        # Find slowest endpoints
        slow_endpoints = sorted(benchmarks.items(), 
                              key=lambda x: x[1].avg_response_time, reverse=True)[:3]
        
        if slow_endpoints:
            report.append("### Slowest Endpoints (Average Response Time)")
            for name, metrics in slow_endpoints:
                report.append(f"- {metrics.operation}: {metrics.avg_response_time*1000:.2f} ms")
            report.append("")
        
        # Find endpoints with highest error rates
        high_error_endpoints = [(name, metrics) for name, metrics in benchmarks.items() 
                               if metrics.error_rate > 0]
        
        if high_error_endpoints:
            report.append("### Endpoints with Errors")
            for name, metrics in high_error_endpoints:
                report.append(f"- {metrics.operation}: {metrics.error_rate:.2f}% error rate")
            report.append("")
        
        # Recommendations based on metrics
        recommendations = []
        
        for name, metrics in benchmarks.items():
            if metrics.avg_response_time > 1.0:  # > 1 second
                recommendations.append(f"Consider optimizing {metrics.operation} (avg: {metrics.avg_response_time*1000:.2f} ms)")
            
            if metrics.error_rate > 5.0:  # > 5% error rate
                recommendations.append(f"Investigate errors in {metrics.operation} ({metrics.error_rate:.2f}% error rate)")
            
            if metrics.requests_per_second < 10 and metrics.total_requests > 100:
                recommendations.append(f"Consider caching for {metrics.operation} (low RPS: {metrics.requests_per_second:.2f})")
        
        if recommendations:
            for rec in recommendations:
                report.append(f"- {rec}")
        else:
            report.append("All endpoints are performing within acceptable limits.")
        
        report.append("")
        
        return "\n".join(report)
    
    def save_benchmark_results(self, benchmarks: Dict[str, PerformanceMetrics], 
                             filename: str = None) -> str:
        """Save benchmark results to file."""
        
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        # Convert to serializable format
        serializable_benchmarks = {}
        for name, metrics in benchmarks.items():
            serializable_benchmarks[name] = {
                'operation': metrics.operation,
                'total_requests': metrics.total_requests,
                'successful_requests': metrics.successful_requests,
                'failed_requests': metrics.failed_requests,
                'avg_response_time': metrics.avg_response_time,
                'min_response_time': metrics.min_response_time,
                'max_response_time': metrics.max_response_time,
                'p95_response_time': metrics.p95_response_time,
                'p99_response_time': metrics.p99_response_time,
                'requests_per_second': metrics.requests_per_second,
                'error_rate': metrics.error_rate,
                'total_duration': metrics.total_duration
            }
        
        with open(filename, 'w') as f:
            json.dump(serializable_benchmarks, f, indent=2)
        
        return filename


# Utility functions for running performance tests
def run_quick_performance_test(base_url: str = "http://localhost:8000") -> Dict[str, PerformanceMetrics]:
    """Run a quick performance test on key endpoints."""
    
    tester = PerformanceTester(base_url)
    
    # Test only the most critical endpoints
    quick_benchmarks = {}
    
    print("Running quick performance test...")
    
    # Health check
    print("Testing health check...")
    quick_benchmarks["health"] = tester.benchmark_endpoint("/health", num_requests=100, concurrent_users=10)
    
    # Get APIs
    print("Testing get APIs...")
    quick_benchmarks["get_apis"] = tester.benchmark_endpoint("/api/apis", num_requests=50, concurrent_users=5)
    
    # Schema discovery
    print("Testing schema discovery...")
    quick_benchmarks["discover"] = tester.benchmark_endpoint(
        "/discover-schema", method="POST",
        data={"url": "https://jsonplaceholder.typicode.com"},
        num_requests=20, concurrent_users=3
    )
    
    return quick_benchmarks


def run_stress_test(base_url: str = "http://localhost:8000", duration_seconds: int = 60) -> PerformanceMetrics:
    """Run a stress test on the health endpoint."""
    
    tester = PerformanceTester(base_url)
    
    print(f"Running stress test for {duration_seconds} seconds...")
    
    # Calculate number of requests based on duration
    # Aim for high RPS during stress test
    target_rps = 100
    num_requests = target_rps * duration_seconds
    
    return tester.benchmark_endpoint(
        "/health", 
        num_requests=num_requests, 
        concurrent_users=50
    )


async def run_async_performance_test(base_url: str = "http://localhost:8000") -> Dict[str, PerformanceMetrics]:
    """Run performance tests using async requests."""
    
    tester = PerformanceTester(base_url)
    
    async_benchmarks = {}
    
    print("Running async performance test...")
    
    # Health check
    async_benchmarks["health_async"] = await tester.benchmark_endpoint_async(
        "/health", num_requests=200, concurrent_users=20
    )
    
    # Get APIs
    async_benchmarks["get_apis_async"] = await tester.benchmark_endpoint_async(
        "/api/apis", num_requests=100, concurrent_users=10
    )
    
    return async_benchmarks


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
        
        if sys.argv[2] == "quick":
            results = run_quick_performance_test(base_url)
            tester = PerformanceTester(base_url)
            report = tester.generate_performance_report(results)
            print(report)
            
        elif sys.argv[2] == "comprehensive":
            tester = PerformanceTester(base_url)
            results = tester.run_comprehensive_benchmark()
            report = tester.generate_performance_report(results)
            print(report)
            
            # Save results
            filename = tester.save_benchmark_results(results)
            print(f"\nResults saved to: {filename}")
            
        elif sys.argv[2] == "stress":
            duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
            result = run_stress_test(base_url, duration)
            print(f"Stress test completed:")
            print(f"  Requests/sec: {result.requests_per_second:.2f}")
            print(f"  Avg response time: {result.avg_response_time*1000:.2f} ms")
            print(f"  Error rate: {result.error_rate:.2f}%")
            
        elif sys.argv[2] == "async":
            results = asyncio.run(run_async_performance_test(base_url))
            tester = PerformanceTester(base_url)
            report = tester.generate_performance_report(results)
            print(report)
            
        else:
            print("Usage: python performance_tests.py <base_url> <quick|comprehensive|stress|async> [duration]")
    else:
        print("Usage: python performance_tests.py <base_url> <quick|comprehensive|stress|async> [duration]")
        print("Example: python performance_tests.py http://localhost:8000 quick")
