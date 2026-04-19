#!/usr/bin/env python3
"""
Generates datasets.json with all folders found in data/
Run: python3 generate_datasets.py
"""

import json
import os
from pathlib import Path

def generate_datasets_json():
    data_dir = Path("data")
    
    if not data_dir.exists():
        print(f"Error: 'data' folder does not exist")
        return
    
    # Find all folders in data/
    datasets = []
    
    for item in sorted(data_dir.iterdir()):
        if item.is_dir():
            # Verify it has data.json inside
            data_json = item / "data.json"
            if data_json.exists():
                datasets.append(item.name)
    
    # Create datasets.json file
    output = {
        "datasets": datasets
    }
    
    with open("datasets.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ datasets.json generated with {len(datasets)} dataset(s):")
    for ds in datasets:
        print(f"   - {ds}")

if __name__ == "__main__":
    generate_datasets_json()
