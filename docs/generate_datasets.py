#!/usr/bin/env python3
"""
Script para generar datasets.json con todas las carpetas encontradas en data/
Ejecutar: python3 generate_datasets.py
"""

import json
import os
from pathlib import Path

def generate_datasets_json():
    data_dir = Path("data")
    
    if not data_dir.exists():
        print(f"Error: La carpeta 'data' no existe")
        return
    
    # Buscar todas las carpetas en data/
    datasets = []
    
    for item in sorted(data_dir.iterdir()):
        if item.is_dir():
            # Verificar que tenga data.json dentro
            data_json = item / "data.json"
            if data_json.exists():
                datasets.append(item.name)
    
    # Crear el archivo datasets.json
    output = {
        "datasets": datasets
    }
    
    with open("datasets.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ datasets.json generado con {len(datasets)} dataset(s):")
    for ds in datasets:
        print(f"   - {ds}")

if __name__ == "__main__":
    generate_datasets_json()
