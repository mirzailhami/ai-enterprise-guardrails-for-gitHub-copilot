from typing import List, Dict

def check_license(files: List[Dict[str, str]], config: Dict) -> List[Dict]:
    restricted = config.get('restricted_licenses', ['gpl', 'agpl'])
    violations = []
    for file_item in files:
        path = file_item['path']
        content = file_item.get('content', '').lower()
        for lic in restricted:
            if lic in content:
                violations.append({
                    'type': 'license',
                    'description': f'Restricted license "{lic.upper()}" detected in {path}',
                    'risk': 'Incompatible license'
                })
    return violations