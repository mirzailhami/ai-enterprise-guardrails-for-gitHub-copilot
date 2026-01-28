import requests
import json
import os
import re
from typing import List, Dict

# Active hosted model (Jan 2026) – good for code review & fixes
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "meta-llama/Llama-3.2-3B-Instruct"  # Your current working model

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
                "Output **only** a valid JSON array of issues. "
                "Each issue must have: "
                '"issue": short description, '
                '"explanation": why it\'s an issue, '
                '"fix": suggested fix snippet, '
                '"reference": link to standard (OWASP, CWE, etc.). '
                "If no issues, return empty array []. "
                "Do not add markdown or extra text."
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
            text = result["choices"][0]["message"]["content"].strip()
            print(f"Raw AI response preview: {text[:300]}...")

            # Clean markdown fences (```json ... ```) if present
            text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.IGNORECASE | re.MULTILINE).strip()

            # Find first valid JSON array
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    issues = json.loads(json_str)
                    if not isinstance(issues, list):
                        raise ValueError("Root is not a list")

                    # Filter only valid issues (must have 'issue' key and non-empty value)
                    valid_issues = [
                        i for i in issues
                        if isinstance(i, dict) and 'issue' in i and i['issue'].strip()
                    ]
                    print(f"AI review found {len(valid_issues)} valid issues (filtered from {len(issues)})")
                    return valid_issues
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"JSON parse error: {e} - raw JSON string: {json_str[:200]}...")
            else:
                print("No JSON array found in AI response")

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