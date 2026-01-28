import requests
import json
import os
from typing import List, Dict

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

# Options:
# - "meta-llama/Llama-3.2-3B-Instruct" (strong reasoning)
# - "mistralai/Mistral-Nemo-Instruct-2407" (good code + chat)
# - "Qwen/Qwen2.5-Coder-7B-Instruct" (code-focused)
HF_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"

def review(diff: str, config: Dict) -> List[Dict]:
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set in .env — skipping AI review")
        return []

    focus = ', '.join(config.get('ai_focus', ['security', 'performance', 'maintainability']))

    # Truncate diff to avoid token limits
    truncated_diff = diff[:4000] + ("... [truncated]" if len(diff) > 4000 else "")

    messages = [
        {
            "role": "system",
            "content": f"You are a senior security and code quality engineer. Review the code diff for {focus}. "
                       "Output ONLY a valid JSON array of issues. Each issue must have: "
                       '"issue": short description, '
                       '"explanation": why it\'s an issue, '
                       '"fix": suggested fix snippet, '
                       '"reference": standard link (e.g. OWASP). '
                       "If no issues, return []."
        },
        {
            "role": "user",
            "content": f"Code diff to review:\n{truncated_diff}"
        }
    ]

    payload = {
        "model": HF_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 600,
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

        # Extract assistant's response
        if 'choices' in result and result['choices']:
            text = result['choices'][0]['message']['content'].strip()
            print(f"Raw AI response preview: {text[:200]}...")

            # Extract JSON array
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                try:
                    issues = json.loads(json_str)
                    if isinstance(issues, list):
                        print(f"AI review found {len(issues)} issues")
                        return issues
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e} - raw: {json_str}")
            else:
                print("No JSON array found in AI response")
        else:
            print("Unexpected response format")

    except requests.HTTPError as e:
        print(f"HF router HTTP error: {e.response.status_code} {e.response.reason}")
        print(f"Response body: {e.response.text[:500]}...")
    except requests.RequestException as e:
        print(f"HF router request failed: {e}")
    except Exception as e:
        print(f"AI review failed: {e}")

    return []  # Fallback