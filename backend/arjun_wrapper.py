import subprocess
import json
from typing import List
from .models import CanonicalParameter

def run_arjun(url: str, output_file: str) -> dict:
    """
    Run Arjun CLI on the given URL and output to a file.
    Returns a dict with keys: success (bool), stderr, stdout.
    """
    try:
        result = subprocess.run(
            ["python", "-m", "arjun", "-u", url, "-o", output_file],
            capture_output=True,
            text=True,
            check=False  # handle errors manually
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}


def parse_arjun_output(file_path: str) -> List[CanonicalParameter]:
    """
    Load Arjun JSON output file and convert to list of CanonicalParameter
    """
    import os
    
    # Check if file exists (Arjun doesn't create file when no params found)
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    parameters = []
    
    # Handle Arjun's actual output format
    for url, url_data in data.items():
        if "params" in url_data:
            for param_name in url_data["params"]:
                param = CanonicalParameter(
                    name=param_name,
                    in_="query",  # Arjun only finds query parameters
                    type_="string",  # Default type
                    required=True,  # Assume required for discovered params
                    description=f"Discovered parameter from {url}",
                    example=None
                )
                parameters.append(param)
    
    return parameters
