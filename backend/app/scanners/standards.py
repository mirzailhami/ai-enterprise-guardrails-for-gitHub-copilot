import ast
import re
from typing import List, Dict

def enforce(file_content: str, config: Dict) -> List[Dict]:
    violations = []
    standards = config.get('standards', {})
    
    print(f"Standards check on content length: {len(file_content)}")
    
    if '\x00' in file_content:
        print("Skipping AST: null bytes detected")
        return violations
    
    try:
        tree = ast.parse(file_content)
        print("AST parsed successfully")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                pattern = standards.get('naming', {}).get('functions', '.*')
                print(f"Checking function: {node.name} against {pattern}")
                if not re.match(pattern, node.name):
                    violations.append({
                        'type': 'naming',
                        'description': f"Invalid function name: {node.name} (expected {pattern})",
                        'location': node.lineno
                    })
    except SyntaxError as e:
        print(f"AST SyntaxError: {e}")
        pass
    
    # Logging check
    if 'import logging' not in file_content and standards.get('logging', {}).get('require'):
        print("Logging missing detected")
        violations.append({
            'type': 'logging',
            'description': 'Missing logging import',
            'severity': 'medium'
        })
    
    print(f"Standards violations: {len(violations)}")
    return violations