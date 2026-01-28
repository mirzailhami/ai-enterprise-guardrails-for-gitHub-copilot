import yaml
import os
from typing import Dict

def load_guardrails(config_path: str = None) -> Dict:
    """Load repo config from YAML; fallback to shared default."""
    # Absolute path from project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_path = os.path.join(project_root, "shared", "configs", "guardrails.yaml")
    
    print(f"Trying to load guardrails from: {default_path}")
    
    path = config_path or default_path
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
            print(f"Loaded config: {data}")
            return data
    
    print("Config file not found — using fallback")
    return {
        'enforcement': 'warning',
        'standards': {},
        'ai_focus': ['security'],
        'restricted_licenses': []
    }