# GitHub Guardrails MVP for TopCoder

Enterprise-grade guardrails for GitHub Copilot: Hybrid AI + static analysis for secure, compliant code in PRs.

## Architecture
- **GitHub App** (TypeScript/Probot): Triggers on PRs, enforces policies, posts comments.
- **Backend** (Python/FastAPI): Scans diffs for security/standards/AI reviews.
- **Integration**: Webhooks → Async API calls → PR annotations/status checks.

## Quick Start
1. Install deps: See below.
2. Run backend: `cd backend && python run.py`
3. Run app: `cd github-app && npm start`
4. Create GitHub App: [Guide](docs/DEPLOYMENT.md)
5. Test: Push to a test repo, open PR.

## Features (MVP)
- Secure scans (Semgrep/Bandit/GitLeaks)
- Standards enforcement (YAML config)
- AI reviews (Hugging Face)
- License checks (Scancode)
- Policies: Advisory/Warning/Blocking + overrides
- Audit logs (SQLite)

## Submission
- Source: This repo
- Deployed URL: [ngrok link or GitHub App URL]
- Demo: Screenshots in docs/