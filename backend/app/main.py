from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import os
from .utils.config import load_guardrails
from .utils.audit import log
from .scanners.secure import scan as secure_scan
from .scanners.standards import enforce
from .scanners.ai_review import review as ai_review
from .compliance.license import check_license

app = FastAPI(title="Guardrails Backend")

class ScanRequest(BaseModel):
    pr_id: str
    diff: str
    files: List[str]
    config_path: str = None  # Optional repo YAML
    is_copilot: bool = False # set true for AI-generated diffs

@app.post("/scan")
async def scan_pr(req: ScanRequest):
    config = load_guardrails(req.config_path)
    violations: List[Dict] = []
    
    # Secure
    violations += secure_scan(req.files, config, req.is_copilot)
    
    # Standards (assume first file content for MVP; in prod, fetch full files from GitHub API)
    if req.files:
        try:
            with open(req.files[0], 'r') as f:
                content = f.read()
            violations += enforce(content, config)
        except FileNotFoundError:
            pass  # Skip if test file missing
    
    # AI
    ai_issues = ai_review(req.diff, config)
    violations += ai_issues
    
    # License
    violations += check_license(req.files, config)
    
    # Audit
    action = config.get('enforcement', 'warning')
    log(req.pr_id, violations, action)
    
    return {"violations": violations, "policy": action, "total": len(violations)}

@app.get("/")
def root():
    return {"msg": "Guardrails Backend Ready 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)