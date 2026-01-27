import ast
import re
from typing import List, Dict

def enforce(file_content: str, config: Dict) -> List[Dict]:
    violations = []
    standards = config.get('standards', {})
    
    # AST parse for Python (extend for other langs later)
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
    except SyntaxError:
        pass  # Non-Python files
    
    # Logging check (simple string match)
    if 'import logging' not in file_content and standards.get('logging', {}).get('require'):
        violations.append({
            'type': 'logging',
            'description': 'Missing logging import',
            'severity': 'medium'
        })
    
    return violations