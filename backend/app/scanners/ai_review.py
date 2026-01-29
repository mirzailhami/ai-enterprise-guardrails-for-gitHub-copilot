import requests
import json
import os
import re
from typing import List, Dict

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
                "Output ONLY a valid JSON array of issues. "
                "Each issue must have: "
                '"issue": short description, '
                '"explanation": why it\'s an issue, '
                '"fix": suggested fix snippet, '
                '"reference": link to standard (e.g. OWASP, CWE). '
                "If no issues, return []. "
                "Do NOT add markdown, code fences, explanations, or extra text."
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
        "max_tokens": 800,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"Calling HF router with model: {HF_MODEL}")
        response = requests.post(HF_ROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        if "choices" in result and result["choices"]:
            raw_text = result["choices"][0]["message"]["content"].strip()
            print(f"Raw AI response preview: {raw_text[:300]}...")

            # Step 1: Remove markdown code fences (```json ... ```) if present
            cleaned_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.IGNORECASE | re.MULTILINE).strip()

            # Step 2: Find the first valid JSON array (handles extra whitespace)
            match = re.search(r'\[\s*(?:{.*?}\s*,\s*)*{.*?}\s*\]', cleaned_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                print(f"Extracted JSON string preview: {json_str[:200]}...")

                try:
                    issues = json.loads(json_str)
                    if not isinstance(issues, list):
                        raise ValueError("Parsed root is not a list")

                    # Filter only valid issues
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
                            'severity': 'medium',  # Default or from config
                            'location': 'N/A',
                            'copilot_flag': False  # AI review is separate from Copilot flag
                        }
                        valid_issues.append(normalized)

                    print(f"AI review found {len(valid_issues)} valid normalized issues")
                    return valid_issues
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"JSON parse error: {e} - raw extracted: {json_str[:200]}...")
            else:
                print("No valid JSON array found in cleaned response")

        else:
            print("Unexpected response format from HF router")

    except requests.HTTPError as e:
        print(f"HF router HTTP error: {e.response.status_code} {e.response.reason}")
        print(f"Response body: {e.response.text[:500]}...")
    except requests.RequestException as e:
        print(f"HF router request failed: {e}")
    except Exception as e:
        print(f"AI review failed: {e}")

    return []  # Fallback: no AI issues