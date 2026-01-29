from typing import List, Dict
import hashlib
from difflib import SequenceMatcher

def check_ip_risk(files: List[Dict[str, str]], config: Dict) -> List[Dict]:
    violations = []
    restricted_keywords = config.get('restricted_keywords', ['proprietary', 'confidential', 'copyright all rights reserved', 'all rights reserved'])
    min_similarity = 0.85  # 85% similar = potential copy

    # Track file hashes and contents for duplicate detection
    file_hashes = {}
    file_contents = {}

    for file_item in files:
        path = file_item.get('path', 'unknown')
        content = file_item.get('content', '')

        # IP keyword risk
        for kw in restricted_keywords:
            if kw.lower() in content.lower():
                violations.append({
                    'type': 'ip_risk',
                    'description': f'Potential proprietary/IP notice "{kw}"',
                    'risk': 'Unlicensed or restricted content',
                    'severity': 'medium',
                    'file_path': path
                })

        # Exact duplicate via hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in file_hashes:
            violations.append({
                'type': 'duplicate_code',
                'description': f'Exact duplicate code in {path} (matches {file_hashes[content_hash]})',
                'risk': 'Potential copied code or redundancy',
                'severity': 'medium',
                'file_path': path
            })
        file_hashes[content_hash] = path
        file_contents[path] = content

        # Near-duplicate (fuzzy similarity to previous files)
        for prev_path, prev_content in file_contents.items():
            if prev_path == path:
                continue
            similarity = SequenceMatcher(None, content, prev_content).ratio()
            if similarity > min_similarity:
                violations.append({
                    'type': 'duplicate_code',
                    'description': f'High similarity ({similarity:.2%}) between {path} and {prev_path}',
                    'risk': 'Possible copied or near-duplicate code',
                    'severity': 'medium',
                    'file_path': path
                })

    return violations