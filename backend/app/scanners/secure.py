import re
import ast
import os
import yaml
from typing import List, Dict

def scan(files: List[Dict[str, str]], config: Dict, is_copilot: bool = False) -> List[Dict]:
    violations = []

    def add_violation(base: Dict):
        violation = base.copy()
        if is_copilot and violation.get('severity') == 'high':
            violation['copilot_flag'] = True
        violations.append(violation)

    # Load extensible security rules from YAML
    rules_path = os.path.join(os.path.dirname(__file__), "../../shared/rules/secure.yaml")
    rules = {}
    if os.path.exists(rules_path):
        try:
            with open(rules_path, 'r') as f:
                rules = yaml.safe_load(f) or {}
            print(f"Loaded {len(rules)} security rule categories from {rules_path}")
        except Exception as e:
            print(f"Error loading secure.yaml: {e}")
    else:
        print(f"secure.yaml not found at {rules_path} — using fallback patterns")

    for file_item in files:
        path = file_item.get('path', 'unknown')
        content = file_item.get('content', '')
        if not content:
            continue

        print(f"Secure scan on {path} ({len(content)} chars)")

        # Apply all regex-based rules from YAML
        for category, rule_list in rules.items():
            for rule in rule_list or []:
                pattern = rule.get('pattern')
                if not pattern:
                    continue
                try:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_no = content[:match.start()].count('\n') + 1
                        base = {
                            'type': rule.get('type', category),
                            'description': rule.get('description', f"{category} detected: {match.group()}"),
                            'location': line_no,
                            'severity': rule.get('severity', 'high'),
                            'cwe': rule.get('cwe', 'N/A'),
                            'owasp': rule.get('owasp', 'N/A')
                        }
                        add_violation(base)
                except re.error as e:
                    print(f"Invalid regex in rule {rule.get('type')}: {e}")

        # Keep AST-based checks (can be moved to YAML later)
        if path.lower().endswith('.py'):
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Unsafe exec/eval
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ['exec', 'eval']:
                        line_no = node.lineno
                        base = {
                            'type': 'unsafe_exec',
                            'description': f"Unsafe {node.func.id} call - potential code injection",
                            'location': line_no,
                            'severity': 'high',
                            'cwe': 'CWE-95',
                            'owasp': 'A03:2021 – Injection'
                        }
                        add_violation(base)

                    # Insecure pickle.loads
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                       isinstance(node.func.value, ast.Name) and node.func.value.id == 'pickle' and node.func.attr == 'loads':
                        line_no = node.lineno
                        base = {
                            'type': 'insecure_deserial',
                            'description': 'Insecure deserialization with pickle.loads - arbitrary code execution risk',
                            'location': line_no,
                            'severity': 'high',
                            'cwe': 'CWE-502',
                            'owasp': 'A08:2021 – Software and Data Integrity Failures'
                        }
                        add_violation(base)
            except SyntaxError as e:
                print(f"AST SyntaxError in {path}: {e}")

    return violations