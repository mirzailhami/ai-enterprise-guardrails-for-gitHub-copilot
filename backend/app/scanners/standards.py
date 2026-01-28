import ast
import re
from typing import List, Dict

def enforce(file_content: str, config: Dict) -> List[Dict]:
    violations = []
    standards = config.get('standards', {})
    
    # Quick safety check: skip if binary-like (contains null bytes)
    if '\x00' in file_content:
        print("Skipping AST parse: file contains null bytes (likely binary)")
        # Optionally add a violation if you want
        # violations.append({'type': 'binary_file', 'description': 'Binary file detected - skipping AST'})
        return violations
    
    # AST parse for Python
    try:
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                pattern = standards.get('naming', {}).get('functions', '.*')
                if not re.match(pattern, node.name):
                    violations.append({
                        'type': 'naming',
                        'description': f"Invalid function name: {node.name} (expected {pattern})",
                        'location': node.lineno
                    })
    except SyntaxError as e:
        print(f"AST parse failed (SyntaxError): {e}")
        pass  # Non-Python or invalid syntax
    
    # Logging check (safe even on binary)
    if 'import logging' not in file_content and standards.get('logging', {}).get('require'):
        violations.append({
            'type': 'logging',
            'description': 'Missing logging import',
            'severity': 'medium'
        })
    
    return violations