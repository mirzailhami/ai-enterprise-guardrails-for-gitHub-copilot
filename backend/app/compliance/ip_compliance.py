from typing import List, Dict
import hashlib
from difflib import SequenceMatcher

def check_ip_risk(files: List[Dict[str, str]], config: Dict) -> List[Dict]:
    violations = []
    restricted_keywords = config.get('restricted_keywords', ['proprietary', 'confidential', 'copyright all rights reserved', 'all rights reserved'])
    min_similarity = 0.85  # adjust as needed (0.8–0.9 range)

    # Track content for cross-file duplicates
    seen_contents = {}  # hash → path

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
                    'severity': 'medium',
                    'file_path': path
                })

        # Exact duplicate across files
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in seen_contents:
            violations.append({
                'type': 'duplicate_code',
                'description': f'Exact duplicate file content in {path} (matches {seen_contents[content_hash]})',
                'risk': 'Potential copied code or redundancy',
                'severity': 'medium',
                'file_path': path
            })
        seen_contents[content_hash] = path

        # Near-duplicate across files (optional — keep if you want)
        for prev_path, prev_hash in seen_contents.items():
            if prev_path == path:
                continue
            similarity = SequenceMatcher(None, content, prev_hash).ratio()
            if similarity > min_similarity:
                violations.append({
                    'type': 'duplicate_code',
                    'description': f'High similarity ({similarity:.2%}) between {path} and {prev_path}',
                    'risk': 'Possible copied or near-duplicate code',
                    'severity': 'medium',
                    'file_path': path
                })

        # Simple within-file duplicate detection (repeated blocks/lines)
        lines = content.splitlines()
        seen_lines = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped:
                if stripped in seen_lines:
                    violations.append({
                        'type': 'duplicate_code',
                        'description': f'Duplicate code block/line in {path} at line {i+1} (seen at line {seen_lines[stripped]})',
                        'risk': 'Potential copied code or redundancy inside file',
                        'severity': 'low',
                        'file_path': path
                    })
                else:
                    seen_lines[stripped] = i + 1

    return violations