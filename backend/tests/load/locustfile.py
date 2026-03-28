#!/usr/bin/env python3
"""
Locust load testing file for APISEC application.
"""

from locust import HttpUser, task, between
import json
import random


class APISECUser(HttpUser):
    """Simulates a user interacting with the APISEC application."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts."""
        # Create a test API for this user
        self.api_id = None
        self.test_api_name = f"LoadTest API {random.randint(1000, 9999)}"
        self.test_api_url = f"https://loadtest{random.randint(1000, 9999)}.example.com"
        self.create_test_api()
    
    def create_test_api(self):
        """Create a test API for load testing."""
        response = self.client.post("/api/apis", data={
            "name": self.test_api_name,
            "base_url": self.test_api_url,
            "description": "API created for load testing"
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                self.api_id = data["api"]["id"]
    
    @task(3)
    def get_all_apis(self):
        """Get all registered APIs."""
        self.client.get("/api/apis")
    
    @task(5)
    def get_api_schemas(self):
        """Get schemas for our test API."""
        if self.api_id:
            self.client.get(f"/api/apis/{self.api_id}/schemas")
    
    @task(2)
    def get_latest_schema(self):
        """Get the latest schema for our test API."""
        if self.api_id:
            self.client.get(f"/api/apis/{self.api_id}/schemas/latest")
    
    @task(4)
    def health_check(self):
        """Perform health check."""
        self.client.get("/health")
    
    @task(1)
    def discover_schema(self):
        """Discover schema for a test URL."""
        test_urls = [
            "https://jsonplaceholder.typicode.com",
            "https://api.github.com",
            "https://httpbin.org",
            "https://reqres.in/api"
        ]
        
        test_url = random.choice(test_urls)
        self.client.post("/discover-schema", json={
            "url": test_url
        })
    
    @task(2)
    def create_new_api(self):
        """Create a new API (occasionally)."""
        api_name = f"Random API {random.randint(1000, 9999)}"
        api_url = f"https://random{random.randint(1000, 9999)}.example.com"
        
        self.client.post("/api/apis", data={
            "name": api_name,
            "base_url": api_url,
            "description": "Randomly created API during load test"
        })
    
    @task(1)
    def runtime_validation(self):
        """Perform runtime validation with sample schema."""
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
        
        self.client.post("/validate-runtime", json={
            "base_url": "https://jsonplaceholder.typicode.com",
            "schema_info": sample_schema
        })


class SchemaComparisonUser(HttpUser):
    """Simulates a user focused on schema comparison operations."""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Create test APIs with schemas for comparison."""
        self.api_ids = []
        self.create_test_apis()
    
    def create_test_apis(self):
        """Create multiple test APIs."""
        for i in range(3):
            response = self.client.post("/api/apis", data={
                "name": f"Comparison API {i}",
                "base_url": f"https://comparison{i}.example.com",
                "description": f"API {i} for schema comparison testing"
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.api_ids.append(data["api"]["id"])
    
    @task(3)
    def compare_schemas(self):
        """Compare schema versions."""
        if len(self.api_ids) >= 1:
            api_id = random.choice(self.api_ids)
            # Try to compare versions 1 and 2 (may not exist, but that's okay for load testing)
            self.client.get(f"/api/schemas/{api_id}/compare/1/2")
    
    @task(2)
    def get_schema_versions(self):
        """Get all schema versions for an API."""
        if len(self.api_ids) >= 1:
            api_id = random.choice(self.api_ids)
            self.client.get(f"/api/apis/{api_id}/schemas")
    
    @task(1)
    def get_specific_schema_version(self):
        """Get a specific schema version."""
        if len(self.api_ids) >= 1:
            api_id = random.choice(self.api_ids)
            version = random.randint(1, 5)
            self.client.get(f"/api/schemas/{api_id}/version/{version}")


class HeavyLoadUser(HttpUser):
    """Simulates heavy load with many concurrent operations."""
    
    wait_time = between(0.5, 2)  # Faster operations for heavy load
    
    @task(4)
    def rapid_health_checks(self):
        """Rapid health checks."""
        self.client.get("/health")
    
    @task(3)
    def rapid_api_listings(self):
        """Rapid API listings."""
        self.client.get("/api/apis")
    
    @task(2)
    def rapid_schema_discovery(self):
        """Rapid schema discovery attempts."""
        test_urls = [
            "https://httpbin.org",
            "https://jsonplaceholder.typicode.com",
            "https://reqres.in/api"
        ]
        
        test_url = random.choice(test_urls)
        self.client.post("/discover-schema", json={
            "url": test_url
        })
    
    @task(1)
    def create_and_delete_apis(self):
        """Create and then delete APIs to test write operations."""
        # Create API
        create_response = self.client.post("/api/apis", data={
            "name": f"Temp API {random.randint(1000, 9999)}",
            "base_url": f"https://temp{random.randint(1000, 9999)}.example.com",
            "description": "Temporary API for load testing"
        })
        
        # If successful, immediately delete it
        if create_response.status_code == 200:
            data = create_response.json()
            if data.get("status") == "success":
                api_id = data["api"]["id"]
                self.client.delete(f"/api/apis/{api_id}", catch_response=True)


class BurstLoadUser(HttpUser):
    """Simulates burst traffic patterns."""
    
    wait_time = between(0.1, 0.5)  # Very fast operations
    
    @task(10)
    def burst_health_checks(self):
        """Burst of health checks."""
        self.client.get("/health")
    
    @task(5)
    def burst_api_queries(self):
        """Burst of API queries."""
        self.client.get("/api/apis")
    
    @task(2)
    def burst_schema_queries(self):
        """Burst of schema queries."""
        # Try random API IDs (most won't exist, but that's okay for load testing)
        api_id = random.randint(1, 100)
        self.client.get(f"/api/apis/{api_id}/schemas", catch_response=True)


# Define user classes for different load testing scenarios
class WebsiteUser(HttpUser):
    """Default user class for general load testing."""
    wait_time = between(1, 3)
    
    tasks = {
        APISECUser: 3,
        SchemaComparisonUser: 1,
        HeavyLoadUser: 0.5
    }
    
    @task
    def default_task(self):
        """Default task when no specific task is selected."""
        self.client.get("/health")


# Performance testing scenarios
class StressTestUser(HttpUser):
    """User for stress testing - maximum load."""
    
    wait_time = between(0.1, 1)  # Minimal wait time
    
    @task(8)
    def stress_health_checks(self):
        """Stress test health checks."""
        self.client.get("/health")
    
    @task(4)
    def stress_api_operations(self):
        """Stress test API operations."""
        # Mix of read operations
        self.client.get("/api/apis")
        api_id = random.randint(1, 50)
        self.client.get(f"/api/apis/{api_id}/schemas", catch_response=True)
    
    @task(2)
    def stress_write_operations(self):
        """Stress test write operations."""
        # Create APIs rapidly
        self.client.post("/api/apis", data={
            "name": f"Stress API {random.randint(1000, 9999)}",
            "base_url": f"https://stress{random.randint(1000, 9999)}.example.com",
            "description": "API created during stress testing"
        }, catch_response=True)


# Custom load testing functions
def run_load_test():
    """Run a standard load test."""
    import os
    from locust import run_single_user
    
    # Set host from environment or use default
    host = os.environ.get("APISEC_HOST", "http://localhost:8000")
    
    # Create a test user and run
    user = APISECUser()
    user.host = host
    run_single_user(user)


def run_stress_test():
    """Run a stress test."""
    import os
    from locust import run_single_user
    
    host = os.environ.get("APISEC_HOST", "http://localhost:8000")
    
    user = StressTestUser()
    user.host = host
    run_single_user(user)


if __name__ == "__main__":
    # This allows running the locustfile directly for testing
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "load":
            run_load_test()
        elif sys.argv[1] == "stress":
            run_stress_test()
        else:
            print("Usage: python locustfile.py [load|stress]")
    else:
        print("Usage: python locustfile.py [load|stress]")
        print("Or run with: locust -f locustfile.py")
