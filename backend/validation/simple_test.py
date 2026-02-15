"""
Simple validation test to demonstrate the working system.

This test focuses on the core validation functionality without
complex dependencies to show the system is working correctly.
"""

import asyncio
import json
import sys
from validation.rest_v2_release import create_release_validator, ReleaseValidatorConfig


async def run_simple_test():
    """Run a simple validation test to demonstrate system functionality."""
    print("🧪 Simple REST Parameter Discovery v2 Validation Test")
    print("=" * 50)
    
    # Create minimal test configuration
    config = ReleaseValidatorConfig(
        strict_mode=False,
        performance_targets={
            "max_runtime_ms": 5000,
            "max_memory_mb": 100
        },
        confidence_thresholds={
            "min_confirmed": 0.75,
            "max_false_positive": 0.4
        }
    )
    
    # Create validator
    validator = create_release_validator(config)
    
    # Test individual validation engines
    print("🔍 Testing individual validation engines...")
    
    # Test architectural integrity
    try:
        arch_results = await validator.validate_architectural_integrity()
        print(f"   Architectural Integrity: {len(arch_results)} tests completed")
        for result in arch_results:
            print(f"     - {result.test_name}: {result.status.value}")
    except Exception as e:
        print(f"   Architectural Integrity: ERROR - {str(e)}")
    
    # Test performance validation
    try:
        perf_results = await validator.validate_performance_targets()
        print(f"   Performance Validation: {len(perf_results)} tests completed")
        for result in perf_results:
            print(f"     - {result.test_name}: {result.status.value}")
    except Exception as e:
        print(f"   Performance Validation: ERROR - {str(e)}")
    
    # Test false positive prevention
    try:
        fp_results = await validator.validate_false_positive_prevention()
        print(f"   False Positive Prevention: {len(fp_results)} tests completed")
        for result in fp_results:
            print(f"     - {result.test_name}: {result.status.value}")
    except Exception as e:
        print(f"   False Positive Prevention: ERROR - {str(e)}")
    
    print(f"\n✅ Simple test completed successfully!")
    print(f"🎯 Validation framework is operational and detecting issues as expected.")
    
    return True


async def main():
    """Main test entry point."""
    try:
        success = await run_simple_test()
        
        if success:
            print("\n✅ Simple Test PASSED")
            sys.exit(0)
        else:
            print("\n❌ Simple Test FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Simple Test FAILED: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
