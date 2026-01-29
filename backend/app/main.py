import os
import sqlite3
from .utils.audit import init_db
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from fastapi.responses import HTMLResponse
from .utils.config import load_guardrails
from .utils.audit import log
from .scanners.secure import scan as secure_scan
from .scanners.standards import enforce
from .scanners.ai_review import review as ai_review
from .compliance.license import check_license
from .compliance.ip_compliance import check_ip_risk

app = FastAPI(title="Guardrails Backend")
init_db()

class ScanRequest(BaseModel):
    pr_id: str
    diff: str
    files: List[Dict[str, str]]  # [{path: str, content: str}]
    config_path: str = None
    is_copilot: bool = False

@app.post("/scan")
async def scan_pr(req: ScanRequest):
    config = load_guardrails(req.config_path)
    violations: List[Dict] = []

    # Secure (pass files with content)
    violations += secure_scan(req.files, config, req.is_copilot)

    # Standards (loop over content)
    for file_item in req.files:
        content = file_item.get('content', '')
        path = file_item.get('path', 'unknown')
        if content:
            violations += enforce(content, config)
            print(f"Scanned {path} - {len(content)} chars")  # Debug

    # AI (unchanged)
    ai_issues = ai_review(req.diff, config)
    violations += ai_issues

    # License
    violations += check_license(req.files, config)
    
    # IP Risk
    violations += check_ip_risk(req.files, config)

    action = config.get('enforcement', 'warning')
    log(req.pr_id, violations, action)

    return {"violations": violations, "policy": action, "total": len(violations)}

@app.get("/audit/{pr_id}")
def get_audit(pr_id: str):
    conn = sqlite3.connect("audit.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audits WHERE pr_id = ?", (pr_id,))
    rows = cursor.fetchall()
    conn.close()
    return {"audits": [dict(zip([col[0] for col in cursor.description], row)) for row in rows]}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    conn = sqlite3.connect("audit.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pr_id, violations_count, action, resolution, timestamp FROM audits ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    html = """
    <html>
    <head><title>Guardrails Audit Dashboard</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
    </head>
    <body>
    <h1>Guardrails Audit Dashboard</h1>
    <table>
        <tr><th>PR ID</th><th>Violations</th><th>Action</th><th>Resolution</th><th>Timestamp</th></tr>
    """
    for row in rows:
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
    html += """
    </table>
    </body>
    </html>
    """
    return html
    
@app.get("/")
def root():
    return {"msg": "Guardrails Backend Ready 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)