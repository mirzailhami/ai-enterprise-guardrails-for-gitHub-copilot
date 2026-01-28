import requests
import json
import os
from typing import List, Dict

# Recommended free models (Hugging Face Inference API)
# - bigcode/starcoder2-7b (code-focused, good for review)
# - codellama/CodeLlama-7b-Instruct-hf (strong reasoning + fixes)
HF_MODEL = "bigcode/starcoder2-7b"  # or "codellama/CodeLlama-7b-Instruct-hf"
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

def review(diff: str, config: Dict) -> List[Dict]:
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set in .env — skipping AI review")
        return []

    focus = ', '.join(config.get('ai_focus', ['security', 'performance', 'maintainability']))
    
    # Truncate diff to avoid token limits (safe for MVP)
    truncated_diff = diff[:3000] + ("... [truncated]" if len(diff) > 3000 else "")

    prompt = f"""
You are a senior security and code quality engineer reviewing this code diff for {focus}.

Diff:
{truncated_diff}

Output **only** a valid JSON array of issues. Each issue must have:
- "issue": short description of the problem
- "explanation": why it's an issue (security/performance/maintainability impact)
- "fix": suggested compliant code fix (snippet or change)
- "reference": link to standard (e.g., OWASP, CWE)

Example:
[
  {{"issue": "Hardcoded API key", "explanation": "Risk of exposure", "fix": "Use os.getenv('API_KEY')", "reference": "OWASP A07:2021"}},
  ...
]

If no issues, return empty array [].
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.9,
            "do_sample": False,
            "return_full_text": False
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"Calling HF model: {HF_MODEL} for AI review")
        response = requests.post(HF_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and result and 'generated_text' in result[0]:
            text = result[0]['generated_text'].strip()
            print(f"Raw AI response: {text[:200]}...")

            # Extract JSON array (robust parsing)
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
            print("Unexpected AI response format")

    except requests.RequestException as e:
        print(f"HF API error: {e}")
    except Exception as e:
        print(f"AI review failed: {e}")

    return []  # Fallback: no AI issues