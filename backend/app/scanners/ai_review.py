import requests
import json
import os
import re
from typing import List, Dict
from json_repair import repair_json

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "meta-llama/Llama-3.2-3B-Instruct"

def review(diff: str, config: Dict) -> List[Dict]:
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set in .env — skipping AI review")
        return []

    focus = ', '.join(config.get('ai_focus', ['security', 'performance', 'maintainability']))

    truncated_diff = diff[:4000] + ("... [truncated]" if len(diff) > 4000 else "")

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a senior security and code quality engineer. "
                f"Review the code diff for {focus}. "
                "Respond with **ONLY** the JSON array — no markdown, no code fences, no extra text, no explanations outside JSON. "
                'Format: [{"issue": "short description", "explanation": "why", "fix": "suggested fix", "reference": "link"}, ...] '
                "If no issues, return []."
            )
        },
        {
            "role": "user",
            "content": f"Code diff to review:\n\n{truncated_diff}"
        }
    ]

    payload = {
        "model": HF_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2000,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"Calling HF router with model: {HF_MODEL}")
        response = requests.post(HF_ROUTER_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()

        if "choices" in result and result["choices"]:
            raw_text = result["choices"][0]["message"]["content"].strip()
            print(f"Raw AI response preview (first 500 chars): {raw_text[:500]}...")

            # Clean markdown fences
            cleaned_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.IGNORECASE | re.MULTILINE).strip()

            print(f"Cleaned AI response length: {len(cleaned_text)} chars")
            print(f"Cleaned AI response preview: {cleaned_text[:500]}...")

            # Very forgiving: grab everything from first [ to last ]
            match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            json_str = match.group(0) if match else cleaned_text

            # Trim trailing junk after last ]
            json_str = re.sub(r'\].*', ']', json_str).strip()

            print(f"Trimmed & cleaned JSON preview: {json_str[:300]}...")

            try:
                issues = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                if repair_json:
                    try:
                        repaired = repair_json(json_str)
                        issues = json.loads(repaired)
                        print("JSON repaired successfully using json_repair")
                    except Exception as repair_e:
                        print(f"Repair failed: {repair_e}")
                        issues = []
                else:
                    issues = []

            if isinstance(issues, list):
                valid_issues = []
                for i in issues:
                    if not isinstance(i, dict) or 'issue' not in i:
                        continue
                    normalized = {
                        'type': 'ai_review',
                        'description': i.get('issue', 'AI-detected issue'),
                        'explanation': i.get('explanation', ''),
                        'fix': i.get('fix', ''),
                        'reference': i.get('reference', 'N/A'),
                        'severity': 'medium',
                        'location': 'N/A',
                        'copilot_flag': False,
                        'file_path': 'PR diff'
                    }
                    valid_issues.append(normalized)

                print(f"AI review found {len(valid_issues)} valid normalized issues")
                return valid_issues
            else:
                print("Parsed result is not a list")

        else:
            print("Unexpected response format from HF router")

    except requests.HTTPError as e:
        print(f"HF router HTTP error: {e.response.status_code} {e.response.reason}")
        print(f"Response body preview: {e.response.text[:500]}...")
    except requests.RequestException as e:
        print(f"HF router request failed: {e}")
    except Exception as e:
        print(f"AI review failed: {e}")