# AI-Powered Enterprise Guardrails for GitHub Copilot
Topcoder Challenge Submission

This MVP provides enterprise-grade guardrails for GitHub Copilot, ensuring secure, compliant, and high-quality code in production workflows. It scans both AI-generated and human-written code in PRs, detects risks (security, standards, licensing, IP), flags Copilot-specific issues, enforces customizable policies, provides AI-assisted explanations and fixes, and logs audits — all while staying developer-friendly and scalable.

### Solution Overview
The system is a hybrid static + AI analysis platform that complements (does not replace) native Copilot:
- Probot GitHub App (TypeScript): Listens to PR/commit events, fetches diffs/files/contents, detects Copilot mode from commit message, calls backend, posts structured markdown table comments + status checks.
- FastAPI Backend (Python): Loads YAML config, performs scans (regex/AST for security/standards, LLM for AI review), returns violations with explanations/fixes, logs audits in SQLite.
- Integration: Webhooks → async scan → PR annotations + policy enforcement + override command (/override).

Key differentiators: Copilot awareness (stricter flagging with 🚨), policy modes (advisory/warning/blocking), extensible YAML rules, audit traceability, and AI-driven feedback.

### Features (All Live in Demo PR)
- Secure coding guardrails: Hardcoded secrets, SQL injection, unsafe exec, insecure deserialization (OWASP/CWE mapped)
- Enterprise standards enforcement: Naming conventions, logging requirements (YAML-configurable)
- AI-assisted code review: Explanations and code fixes (Llama-3.2-3B-Instruct via Hugging Face router)
- License & IP compliance: Restricted licenses + basic IP/duplicate detection
- Copilot awareness: Detects AI-generated code via commit message → stricter flagging (🚨 Yes on high-severity)
- Policy-based enforcement: Advisory / warning / blocking modes + user override (/override)
- PR integration: Markdown table comments (with filename in description, details for fixes/references), status checks (green/red/yellow)
- Traceability: Audit logs in SQLite (exportable)
- Extensibility: YAML rules for new patterns, languages, frameworks
- Developer-friendly: Clear explanations, fix suggestions, minimal disruption, override escape hatch

### Live Demo PR (Real Scan & Enforcement)
https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/pull/2

- 38 violations detected (secure + standards + license/IP + AI)
- Copilot Mode: Enabled (from commit message keyword)
- Blocking policy enforced — red status check ("Merge blocked")
- Override tested — /override comment → green status + reply: "Override approved—proceed with caution."
- Table with filename in Description (e.g., "Insecure deserialization with pickle.loads in backend/test.py"), AI fixes in Details

### Architecture Diagram
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
    J["Secure Scan<br>(YAML rules + regex/AST)"]
    K["Standards Enforcement<br>(naming, logging from YAML)"]
    L["AI Review<br>(Hugging Face router + Llama-3.2)"]
    M["License & IP Check<br>(regex + duplicate detection)"]
    N["Audit Log (SQLite)"]
    O["Return JSON: violations, policy, total"]
    P["Probot receives response"]
    Q["Post PR Comment<br>(markdown table with filename & details)"]
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

### Quick Start (Local Deployment Guide)

1. Backend (Python/FastAPI)
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python run.py
   → Runs on http://localhost:8000 (Swagger: /docs)

2. Probot GitHub App (TypeScript)
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

### Bonus Features
- Visual Audit Dashboard: http://localhost:8000/dashboard (HTML summary of audits)
- Audit Export: sqlite3 audit.db ".mode csv" ".headers on" "SELECT * FROM audits;" > audit_export.csv
- Per-repo rule packs: Use config_path (e.g., shared/rules/banking.yaml) for specialized projects

### Submission Details
- Source Code: https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot
- Deployed URLs:
  - Backend: http://localhost:8000/docs (Swagger UI)
  - Probot webhook: https://4a0b241fab57.ngrok-free.app (ngrok tunnel)
- Demo PR: https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/pull/2
  - Shows real scan, table comment with filenames, Copilot flagging, blocking status, override success
- Screenshots (in docs/ folder):
  - PR comment with violation table
  - Red blocking status check
  - Override comment + green status
  - Probot logs (scan + posted)
  - Backend logs (config loaded + violations + AI review)