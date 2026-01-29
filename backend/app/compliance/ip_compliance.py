from typing import List, Dict
import hashlib
from difflib import SequenceMatcher

def check_ip_risk(files: List[Dict[str, str]], config: Dict) -> List[Dict]:
    violations = []
    restricted_keywords = config.get('restricted_keywords', ['proprietary', 'confidential', 'copyright all rights reserved', 'all rights reserved'])
    min_similarity = 0.85  # 85% similar = potential copy

    # Hash-based exact duplicate detection
    file_hashes = {}
    for file_item in files:
        path = file_item.get('path', 'unknown')
        content = file_item.get('content', '')

        # IP keyword risk
        for kw in restricted_keywords:
            if kw.lower() in content.lower():
                violations.append({
                    'type': 'ip_risk',
                    'description': f'Potential proprietary/IP notice "{kw}" in {path}',
                    'risk': 'Unlicensed or restricted content',
                    'severity': 'medium'
                })

        # Exact duplicate via hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in file_hashes:
            violations.append({
                'type': 'duplicate_code',
                'description': f'Exact duplicate code in {path} (matches {file_hashes[content_hash]})',
                'risk': 'Potential copied code or redundancy',
                'severity': 'medium'
            })
        file_hashes[content_hash] = path

        # Near-duplicate (fuzzy similarity to previous files)
        if len(file_hashes) > 1:
            prev_path, prev_hash = list(file_hashes.items())[-2]
            similarity = SequenceMatcher(None, content, prev_hash).ratio()
            if similarity > min_similarity:
                violations.append({
                    'type': 'duplicate_code',
                    'description': f'High similarity ({similarity:.2%}) between {path} and {prev_path}',
                    'risk': 'Possible copied or near-duplicate code',
                    'severity': 'medium'
                })

    return violations