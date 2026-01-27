from typing import List, Dict

def check_license(files: List[str], config: Dict) -> List[Dict]:
    restricted = config.get('restricted_licenses', [])
    violations = []
    # Simple regex stub: Scan for known license headers
    for file in files:
        try:
            with open(file, 'r') as f:  # Assume local files for test
                content = f.read()
            if any(lic in content.lower() for lic in restricted):
                violations.append({'type': 'license', 'risk': 'Restricted license detected'})
        except FileNotFoundError:
            pass  # Skip non-existent files
    return violations