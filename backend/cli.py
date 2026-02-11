#!/usr/bin/env python3
"""
APISec Parameter Inference CLI

Usage: python -m backend.cli --url <URL> --method <METHOD> [--time <SECONDS>]
"""

import argparse
import json
import sys
import os
from typing import Dict, Any

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="APISec Parameter Inference CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "--url",
        required=True,
        help="Target API endpoint URL"
    )
    
    parser.add_argument(
        "--method", 
        required=True,
        choices=["GET", "POST", "get", "post"],
        help="HTTP method to use"
    )
    
    # Optional arguments
    parser.add_argument(
        "--time",
        type=int,
        default=30,
        help="Maximum execution time in seconds (default: 30)"
    )
    
    # Parse arguments
    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse handles help/usage, exit with code 1
        sys.exit(1)
    
    # Normalize method
    method = args.method.upper()
    
    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://", file=sys.stderr)
        sys.exit(1)
    
    # Validate time
    if args.time <= 0:
        print("Error: Time must be positive", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Import and run inference
        from backend.app import run_inference
        
        result = run_inference(args.url, method, args.time)
        
        # Output pretty JSON
        print(json.dumps(result, indent=2))
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
