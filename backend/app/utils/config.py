import yaml
import os
from typing import Dict

def load_guardrails(config_path: str = None) -> Dict:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_path = os.path.join(project_root, "shared", "configs", "guardrails.yaml")
    
    print(f"Project root detected: {project_root}")
    print(f"Attempting to load from: {default_path}")
    
    if os.path.exists(default_path):
        try:
            with open(default_path, 'r') as f:
                data = yaml.safe_load(f)
                print(f"Successfully loaded config: {data}")
                return data
        except Exception as e:
            print(f"YAML load error: {e}")
    else:
        print(f"Config file not found at {default_path}")
    
    print("Falling back to defaults")
    return {
        'enforcement': 'warning',
        'standards': {},
        'ai_focus': ['security'],
        'restricted_licenses': []
    }