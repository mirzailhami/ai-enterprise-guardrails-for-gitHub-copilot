# AI-Powered Enterprise Guardrails for GitHub Copilot
TopCoder Challenge Submission

This MVP provides enterprise-grade guardrails for GitHub Copilot, ensuring secure, compliant, and high-quality code in production workflows. It scans both AI-generated and human-written code in PRs, detects risks (security, standards, licensing), flags Copilot-specific issues, enforces customizable policies, and logs audits — all while staying developer-friendly.

### Solution Overview
The system is a hybrid static + AI analysis platform that complements (does not replace) Copilot:
- Probot GitHub App (TypeScript): Listens to PR/commit events, fetches diffs/files, calls backend, posts comments/tables/status checks.
- FastAPI Backend (Python): Performs scans (regex/AST for security/standards, future LLM for explanations), loads YAML config, logs audits in SQLite.
- Integration: Webhooks → async scan → PR annotations + status enforcement + override command (/override).
- Key differentiators: Copilot awareness (flags AI code with 🚨), policy modes (warning/blocking), YAML-configurable rules, audit traceability.

### Features (All Live in Demo PR)
- Secure coding guardrails: Hardcoded secrets, SQL injection, unsafe exec, insecure deserialization (OWASP/CWE mapped)
- Enterprise standards enforcement: Naming conventions, logging requirements (YAML-defined)
- Copilot awareness: Detects AI-generated code via commit message → stricter flagging (🚨 Yes on high-severity)
- Policy-based enforcement: Advisory / warning / blocking modes + user override (/override)
- PR integration: Markdown table comments, status checks (green/red/yellow), inline feedback
- Traceability: Audit logs in SQLite (violations, actions, resolution)
- Extensibility: YAML rules for new patterns, languages, frameworks
- Developer-friendly: Clear explanations, minimal disruption, override escape hatch

### Live Demo PR (Real Scan & Enforcement)
https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/pull/2

- 15 violations detected (secure + standards)
- Copilot Mode: Enabled (from commit message keyword)
- Blocking policy enforced — red status check ("Merge blocked")
- Override tested — /override comment → green status + reply: "Override approved—proceed with caution."
- Table comment with type, description, location, severity, Copilot flag (🚨 Yes on AI-flagged highs)

### Architecture Diagram

```mermaid
flowchart TD
    A["GitHub Repo/PR Event<br>(opened, reopened, synchronize)"]
    B["Probot GitHub App (TypeScript)"]
    C["Webhook Trigger (ngrok)"]
    D["Fetch Diff (Octokit)"]
    E["Fetch Changed Files + Contents (getContent, base64 decode)"]
    F["Detect Copilot Mode<br>(commit message keyword)"]
    G["POST /scan to Backend<br>(send files as [{path, content}])"]
    H["FastAPI Backend (Python)"]
    I["Load Config<br>(shared/configs/guardrails.yaml)"]
    J["Secure Scan<br>(regex for secrets/injection/exec, AST for exec/deserial)"]
    K["Standards Enforcement<br>(naming, logging from YAML)"]
    L["Future AI Review<br>(Hugging Face LLM)"]
    M["License Check<br>(regex on content)"]
    N["Audit Log (SQLite)"]
    O["Return JSON: violations, policy, total"]
    P["Probot receives response"]
    Q["Post PR Comment<br>(markdown table with Copilot? 🚨 Yes/No)"]
    R["Set Commit Status Check<br>(success/warning/failure)"]
    S["User Override<br>(/override comment → success status)"]
    
    A --> B
    B --> C
    B --> D
    B --> E
    B --> F
    B --> G
    G --> H
    H --> I
    H --> J
    H --> K
    H --> L
    H --> M
    H --> N
    H --> O
    O --> P
    P --> Q
    P --> R
    P --> S

### Quick Start (Local Dev)

1. Backend (scans & logic)
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python run.py
   → Runs on http://localhost:8000 (Swagger: /docs)

2. Probot GitHub App (webhooks & PR actions)
   cd github-app
   npm install
   npm run build
   npm start
   → Runs on http://localhost:3000

3. Expose webhook publicly (use ngrok)
   ngrok http 3000
   → Copy HTTPS URL (e.g. https://abc123.ngrok-free.app)

4. Update GitHub App
   Go to https://github.com/settings/apps/ai-enterprise-guardrails
   Edit → Webhook URL: paste ngrok HTTPS
   Save

5. Install app on your repo
   App page → Install App → Select ai-enterprise-guardrails-for-gitHub-copilot
   Open a PR → Auto-scan + comment + status!

### Configuration
All rules/policies loaded from shared/configs/guardrails.yaml:
enforcement: blocking           # advisory / warning / blocking
standards:
  naming:
    functions: "^[a-z_]+$"      # snake_case only
  logging:
    require: "import logging"   # must import logging
ai_focus: [security, performance]
restricted_licenses: [gpl-3.0, agpl-3.0]

### Submission Details
- Source Code: https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot
- Deployed URLs:
  - Backend: http://localhost:8000/docs (Swagger UI)
  - Probot webhook: https://4a0b241fab57.ngrok-free.app (ngrok tunnel)
- Demo PR: https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/pull/2
  - Shows real scan, table comment, Copilot flagging, blocking status, and /override success
- Screenshots (add to docs/ folder):
  - PR comment with violation table
  - Red blocking status check
  - Override comment + green status
  - Probot logs (scan + posted)
  - Backend logs (config loaded + violations)

### What's Next (Optional Polish)
- Add Hugging Face AI review (HF_TOKEN in backend → explanations/fixes)
- Export audit logs to CSV (add endpoint in main.py)
- Pre-built rule packs for banking/healthcare (YAML files in shared/rules/)