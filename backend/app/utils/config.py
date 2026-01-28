import yaml
import os
from typing import Dict

def load_guardrails(config_path: str = None) -> Dict:
    default_path = "../../shared/configs/guardrails.yaml"
    path = config_path or os.path.abspath(default_path)
    print(f"Trying to load guardrails from: {path}")
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
            print(f"Loaded config: {data}")
            return data
    print("Config file not found — using fallback")
    return {'enforcement': 'warning', 'standards': {}, 'ai_focus': ['security'], 'restricted_licenses': []}