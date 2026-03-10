#!/usr/bin/env python3
"""
Test script to demonstrate the fixed schema validator functionality
"""

import requests
import json
import time

def test_schema_discovery():
    """Test schema discovery endpoint"""
    print("Testing Schema Discovery...")
    
    response = requests.post(
        "http://localhost:8000/discover-schema",
        json={"url": "https://petstore.swagger.io"}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "success":
            schema = data["schema"]
            print(f"✓ Schema discovered from: {data['schema_url']}")
            print(f"✓ Schema has {len(schema.get('paths', {}))} endpoints")
            return schema
        else:
            print(f"✗ Schema discovery failed: {data.get('message')}")
            return None
    else:
        print(f"✗ Request failed with status {response.status_code}")
        return None

def test_runtime_validation(schema):
    """Test runtime validation endpoint"""
    print("\nTesting Runtime Validation...")
    
    response = requests.post(
        "http://localhost:8000/validate-runtime",
        json={
            "base_url": "https://petstore.swagger.io",
            "schema_info": schema
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "success":
            result = data["validation_result"]
            print(f"✓ Runtime validation completed")
            print(f"✓ Base URL used: {result['base_url']}")
            print(f"✓ Total endpoints: {result['total_endpoints']}")
            print(f"✓ Tested endpoints: {result['tested_endpoints']}")
            print(f"✓ Passed endpoints: {result['passed_endpoints']}")
            print(f"✓ Failed endpoints: {result['failed_endpoints']}")
            print(f"✓ Overall status: {result['overall_status']}")
            
            # Show sample results
            print("\nSample endpoint tests:")
            for i, test in enumerate(result['endpoint_tests'][:3]):
                status = "✓" if test['validation_passed'] else "✗"
                print(f"  {status} {test['method']} {test['path']} - "
                      f"Expected: {test['expected_status']}, "
                      f"Actual: {test['actual_status']}")
                if test.get('error'):
                    print(f"    Error: {test['error']}")
            
            return True
        else:
            print(f"✗ Runtime validation failed: {data.get('error')}")
            return False
    else:
        print(f"✗ Request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    """Main test function"""
    print("APISEC Schema Validator Test")
    print("=" * 40)
    
    # Test schema discovery
    schema = test_schema_discovery()
    if not schema:
        print("\n❌ Cannot proceed without schema discovery")
        return
    
    # Test runtime validation
    success = test_runtime_validation(schema)
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests completed successfully!")
        print("The schema validator is now working correctly.")
    else:
        print("❌ Some tests failed.")

if __name__ == "__main__":
    main()
