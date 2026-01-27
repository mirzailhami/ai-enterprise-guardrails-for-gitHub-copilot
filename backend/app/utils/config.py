import yaml
import os
from typing import Dict

def load_guardrails(config_path: str = None) -> Dict:
    """Load repo config from YAML; fallback to shared default."""
    default_path = "../../shared/configs/guardrails.yaml"  # Relative to backend
    path = config_path or os.path.abspath(default_path)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return {'enforcement': 'warning', 'standards': {}, 'ai_focus': ['security'], 'restricted_licenses': []}