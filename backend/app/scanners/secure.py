import re
import ast
import os
from typing import List, Dict

def scan(files: List[str], config: Dict, is_copilot: bool = False) -> List[Dict]:
    violations = []
    
    def add_violation(base_violation: Dict):
        violation = base_violation.copy()
        if is_copilot and violation.get('severity') == 'high':
            violation['copilot_flag'] = True
        violations.append(violation)
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            secret_patterns = [
                r'sk-\w{20,}',  # Standalone OpenAI keys
                r'api_key\s*=\s*["\'][\w\-]+["\']',  # Full assignments
                r'sk-\w{20,}',  # OpenAI secrets (CWE-798)
                r'api_key\s*=\
                s*["\'][\w\-]+["\']',  # Generic API keys
                r'password\s*=\s*["\'][^"\']+["\']'  # Hardcoded passwords
            ]
            for pattern in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_no = content[:match.start()].count('\n') + 1
                    base = {
                        'type': 'secrets',
                        'description': f"Hardcoded secret detected: {match.group()}",
                        'location': line_no,
                        'severity': 'high',
                        'cwe': 'CWE-798',
                        'owasp': 'A07:2021 – Identification and Authentication Failures'
                    }
                    add_violation(base)  # Use helper
            
            sql_patterns = [
                r'SELECT\s+\*.*f["\']?\{[^}]+\}["\']?',  # f-string SQL with var
                r'SELECT\s+\*.*\+\s*user_input'  # Concat style
            ]
            for pattern in sql_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_no = content[:match.start()].count('\n') + 1
                    base = {
                        'type': 'sql_injection',
                        'description': f"Potential SQL injection pattern: {match.group()}",
                        'location': line_no,
                        'severity': 'high',
                        'cwe': 'CWE-89',
                        'owasp': 'A03:2021 – Injection'
                    }
                    add_violation(base)
            
            unsafe_patterns = [
                r'os\.system\s*\(',  # os.system (CWE-78)
                r'subprocess\.call\s*\([^,]+shell=True'  # Subprocess with shell
            ]
            for pattern in unsafe_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_no = content[:match.start()].count('\n') + 1
                    base = {
                        'type': 'unsafe_exec',
                        'description': f"Unsafe command execution: {match.group()}",
                        'location': line_no,
                        'severity': 'high',
                        'cwe': 'CWE-78',
                        'owasp': 'A03:2021 – Injection'
                    }
                    add_violation(base)
            
            # AST for unsafe exec/deserial
            if file_path.endswith('.py'):
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Unsafe exec
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ['exec', 'eval']:
                        line_no = getattr(node, 'lineno', 'N/A')
                        base = {
                            'type': 'unsafe_exec',
                            'description': f"Unsafe {node.func.id} call - potential code injection",
                            'location': line_no,
                            'severity': 'high',  # High for injection risk
                            'cwe': 'CWE-95',
                            'owasp': 'A03:2021 – Injection'
                        }
                        add_violation(base)
                    
                    # Insecure deserial
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                       isinstance(node.func.value, ast.Name) and node.func.value.id == 'pickle' and node.func.attr == 'loads':
                        line_no = getattr(node, 'lineno', 'N/A')
                        base = {
                            'type': 'insecure_deserial',
                            'description': 'Insecure deserialization with pickle.loads - arbitrary code execution risk',
                            'location': line_no,
                            'severity': 'high',
                            'cwe': 'CWE-502',
                            'owasp': 'A08:2021 – Software and Data Integrity Failures'
                        }
                        add_violation(base)
        
        except FileNotFoundError:
            pass
    
    return violations