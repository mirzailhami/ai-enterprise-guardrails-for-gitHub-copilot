import requests
import json
import os
from typing import List, Dict

HF_URL = "https://api-inference.huggingface.co/models/bigcode/starcoder"  # Free code model
HF_TOKEN = os.getenv('HF_TOKEN')  # Optional; set in .env

def review(diff: str, config: Dict) -> List[Dict]:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    focus = ', '.join(config.get('ai_focus', ['security']))
    
    prompt = f"""
    Review this code diff for {focus}:
    {diff[:2000]}  # Truncate for MVP
    
    Output JSON array: [{{"issue": "desc", "explanation": "why", "fix": "code snippet", "reference": "OWASP link"}}]
    """
    
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 300, "temperature": 0.1}}
    
    try:
        response = requests.post(HF_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()[0]['generated_text']
            # Crude parse (improve with regex/json if needed)
            start = result.find('[{') 
            end = result.find('}]') + 2
            if start != -1 and end != -1:
                return json.loads(result[start:end])
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        pass
    
    return []  # Fallback