from typing import List, Dict

def check_license(files: List[Dict[str, str]], config: Dict) -> List[Dict]:
    restricted = config.get('restricted_licenses', ['gpl', 'agpl', 'lgpl'])
    violations = []

    for file_item in files:
        path = file_item.get('path', 'unknown')
        content = file_item.get('content', '').lower()

        # License detection
        for lic in restricted:
            if lic in content:
                violations.append({
                    'type': 'license',
                    'description': f'Restricted license "{lic.upper()}" detected',
                    'risk': 'Incompatible license – may violate enterprise policy',
                    'severity': 'high',
                    'file_path': path
                })

        # Basic IP/copyright risk (simple keyword check)
        ip_keywords = ['copyright', 'proprietary', 'confidential', 'all rights reserved']
        for kw in ip_keywords:
            if kw in content and 'license' not in content:
                violations.append({
                    'type': 'ip_risk',
                    'description': f'Potential IP/copyright notice "{kw}" in {path} without clear license',
                    'risk': 'Possible unlicensed proprietary code',
                    'severity': 'medium',
                    'file_path': path
                })

    return violations