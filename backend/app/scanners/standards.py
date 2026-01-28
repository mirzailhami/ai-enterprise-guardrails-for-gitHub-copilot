import ast
import re
from typing import List, Dict

def enforce(file_content: str, config: Dict) -> List[Dict]:
    violations = []
    standards = config.get('standards', {})
    
    print(f"Applying standards rules from config: {standards}")
    
    if '\x00' in file_content:
        print("Skipping standards AST: null bytes detected (likely binary)")
        return violations
    
    try:
        tree = ast.parse(file_content)
        print("Standards AST parsed successfully")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                pattern = standards.get('naming', {}).get('functions', '.*')
                print(f"Checking function: {node.name} against pattern: {pattern}")
                if not re.match(pattern, node.name):
                    violations.append({
                        'type': 'naming',
                        'description': f"Invalid function name: {node.name} (expected {pattern})",
                        'location': node.lineno,
                        'severity': 'medium'  # can be configurable
                    })
    except SyntaxError as e:
        print(f"Standards AST SyntaxError: {e} - skipping")
        pass
    
    # Logging check (only on Python files or if content looks like code)
    if 'import logging' not in file_content and standards.get('logging', {}).get('require'):
        print("Logging missing detected")
        violations.append({
            'type': 'logging',
            'description': 'Missing logging import',
            'severity': 'medium'
        })
    
    print(f"Standards violations found: {len(violations)}")
    return violations