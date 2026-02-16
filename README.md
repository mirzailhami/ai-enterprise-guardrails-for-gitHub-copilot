<div align="center">

# AI-Powered Enterprise Guardrails for GitHub Copilot

<img src="https://img.shields.io/badge/🥇%201st%20Place-Topcoder%20Challenge-gold?style=for-the-badge&logo=topcoder&logoColor=white&labelColor=000000" alt="1st Place Winner" width="300"/>

**1st Place Winner** – Topcoder Challenge: Enterprise Guardrails for GitHub Copilot  
[View Official Challenge →](https://www.topcoder.com/challenges/54a459e5-ddc4-4e56-8fe9-09e0b5506e95?tab=details)

**MVP / Proof-of-Concept** — A functional prototype demonstrating enterprise-grade protection for GitHub Copilot workflows.

<a href="https://github.com/apps/copilot-shield/installations/new">
  <img src="https://img.shields.io/badge/Install%20the%20App-blue?style=for-the-badge&logo=github&logoColor=white" alt="Install App">
</a>

[![GitHub stars](https://img.shields.io/github/stars/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot?style=flat-square&logo=github)](https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot?style=flat-square&logo=github)](https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/network/members)
[![License](https://img.shields.io/github/license/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square)](backend/requirements.txt)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green?style=flat-square)](github-app/package.json)

**Protect enterprises from risks in AI-generated code** — hybrid static + AI analysis, Copilot-aware flagging, policy enforcement, audit logs, and developer-friendly feedback.

</div>

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Live Demo](#live-demo)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Probot GitHub App Setup](#probot-github-app-setup)
  - [Create & Configure GitHub App](#create--configure-github-app)
  - [GitHub App Permissions & Events](#github-app-permissions--events)
  - [Expose Webhook (ngrok)](#expose-webhook-ngrok)
  - [Install & Test](#install--test)
- [Configuration](#configuration)
- [Bonus Features](#bonus-features)
- [Verification](#verification)
- [Deployed URLs](#deployed-urls)
- [Using on Other Repos](#using-on-other-repos)
- [Contributing](#contributing)
- [License](#license)

## Overview

This is a **proof-of-concept MVP** that won **1st place** in the Topcoder challenge for Enterprise Guardrails for GitHub Copilot.

It demonstrates a **hybrid static + AI platform** that complements (does not replace) native Copilot by:
- Scanning both human-written and AI-generated code in PRs/commits
- Detecting security, compliance, licensing, and IP risks
- Providing AI-assisted explanations and fixes
- Enforcing organization policies with override capability
- Logging audits for traceability

Built with **Python (FastAPI)** + **TypeScript (Probot)** — lightweight, local-first, and extensible.

## Features

- Secure Coding Guardrails — secrets, SQL injection, unsafe exec, insecure deserialization (OWASP/CWE mapped)
- Enterprise Standards — naming conventions, logging requirements (YAML-configurable)
- AI-Assisted Review — contextual explanations + compliant fixes (Llama-3.2-3B-Instruct via Hugging Face)
- License & IP Compliance — restricted licenses + basic duplicate detection
- Copilot Awareness — detects AI-generated code → stricter flagging (🚨 Yes on high-severity)
- Policy Enforcement — advisory/warning/blocking + `/override`
- PR & Commit Integration — structured table comments + status checks
- Traceability — SQLite audit logs (exportable)
- Extensibility — YAML rules + per-repo config overrides
- Developer-Friendly — inline feedback, explanations, fix suggestions, override escape hatch

## Live Demo

**Demo Pull Request #3** (real bot scan & enforcement):  
https://github.com/mirzailhami/ai-enterprise-guardrails-for-gitHub-copilot/pull/3#issuecomment-3815941417

**Highlights:**
- 10 violations detected (secure + standards + AI)
- Copilot Mode: Enabled → 🚨 Yes on high-severity
- Blocking policy → red status check ("Merge blocked")
- `/override` → green status + reply
- Table with filenames in description, AI fixes/explanations/references in details

## Architecture

The system separates concerns cleanly:

- GitHub webhook → Probot (TypeScript) → FastAPI backend (Python) → scan → results → PR comment + status

→ Open [Architecture Diagram](https://mermaid.ai/d/0e4d5783-ef35-4af5-895b-ae4c10dc726f)

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- GitHub account + Personal Access Token (classic, repo scope)
- ngrok (for local webhook testing)
- Hugging Face token (using model: `meta-llama/Llama-3.2-3B-Instruct` or any other model)

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```
→ Open http://localhost:8000/docs (Swagger UI)

### Probot GitHub App Setup
```
cd github-app
npm install
npm run build
npm start
```
→ Runs on http://localhost:3000

**Create .env in github-app/**
```
APP_ID=your_app_id
PRIVATE_KEY_PATH=./private-key.pem
WEBHOOK_SECRET=your_webhook_secret
GITHUB_TOKEN=your_pat_with_repo_scope
BACKEND_URL=http://localhost:8000
```

How to obtain these values:
- **APP_ID**: From GitHub → Settings → Developer settings → GitHub Apps → your app → App ID
- **PRIVATE_KEY_PATH**: Path to your app's private key PEM file (download from GitHub App settings → Generate a private key)
- **WEBHOOK_SECRET**: Set when creating the GitHub App (or generate one and update in GitHub App settings)
- **GITHUB_TOKEN**: Personal Access Token (classic) with repo scope (from GitHub → Settings → Developer settings → Personal access tokens)
- **BACKEND_URL**: Use [http://localhost:8000](http://localhost:8000) locally or your ngrok URL for public webhook

### Create & Configure GitHub App
- Go to GitHub → Settings → Developer settings → GitHub Apps → New GitHub App
- Fill in the form:
  - GitHub App name: e.g., "Copilot Shield"
  - Homepage URL: your repo URL
  - Callback URL: (optional, leave blank for webhook-only)
  - Webhook → Active: check the box
  - Webhook secret: generate or set one (copy to .env as WEBHOOK_SECRET)
  - Permissions: see section below
  - Events: see section below
  - Where can this app be installed: Only on this account or Any account

### GitHub App Permissions & Events
**Repository Permissions** (minimum required):
- Contents → Read-only (fetch file contents/diffs)
- Pull requests → Read & write (post comments, read PR data)
- Commit statuses → Read & write (set green/red checks)
- Issues → Read & write (create PR comments)
- Metadata → Read-only (required by GitHub)

**Subscribed Events:**
- Pull request (opened, reopened, synchronize) — PR lifecycle & commit pushes to PR branches
- Issue comment (created) — detect /override command
- Push — individual commit pushes (optional standalone branch scans)

These are the minimum needed — no over-permissions requested.

### Expose Webhook (ngrok)
```
ngrok http 3000
```
→ Copy HTTPS URL (e.g. https://abc123.ngrok-free.app)

**Update GitHub App**
- Go to your app settings (eq. https://github.com/settings/apps/copilot-shield)
- Edit → Webhook URL: paste ngrok HTTPS → Save

## Install & Test
- App page → Install App → Select your repo
- Open a PR or push a commit → Auto-scan + comment + status check

**Troubleshooting**
- 400 on webhook? Check .env (tokens, BACKEND_URL), ngrok status, and GitHub webhook deliveries.
- No scan? Verify app installation + webhook delivery in GitHub App settings.
- ECONNREFUSED? Ensure backend runs on 127.0.0.1:8000 (not just ::1 IPv6).

## Configuration
```
# shared/configs/guardrails.yaml
enforcement: blocking
standards:
  naming:
    functions: "^[a-z_]+$"
  logging:
    require: "import logging"
ai_focus: [security, performance]
restricted_licenses: [gpl-3.0, agpl-3.0]
```

## Bonus Features
- Audit Dashboard: http://localhost:8000/dashboard (HTML summary)
- Audit Export: `sqlite3 audit.db ".mode csv" ".headers on" "SELECT * FROM audits;" > audit_export.csv`
- Per-repo rule packs: Use `config_path` (e.g. `shared/rules/banking.yaml`)

## Verification
- Open demo PR #3 → see bot comment with table, status check, Copilot flag
- Run locally → test PR in your repo → verify scan/comment/status
- Check http://localhost:8000/docs → Swagger UI for /scan endpoint
- View dashboard: http://localhost:8000/dashboard

## Deployed URLs
- Backend Swagger: https://ai-enterprise-guardrails-for-github.onrender.com/docs
- Audit Dashboard: https://ai-enterprise-guardrails-for-github.onrender.com/dashboard
- Probot Webhook: https://guardrails-probot.onrender.com

> Free tier services may sleep after inactivity — first request can take 10–60 seconds.

## Using on Other Repos

The GitHub App is now **publicly installable** — anyone can add it to their repositories. App will then automatically scan their PRs and commits.

### How to Install

1. Use this direct install link:  
   https://github.com/apps/copilot-shield/installations/new
2. Log in to GitHub (if not already)
3. Choose your account or organization
4. Select which repositories to enable (or "All repositories")
5. Click **Install**

Once installed:
- The bot scans every PR (opened/reopened/synchronize) and push event
- You’ll see violation tables, Copilot flags (🚨), status checks, and more
- Customize per-repo rules by adding `.github/guardrails.yaml` in your repo root

**Example `.github/guardrails.yaml` (override defaults):**
```
enforcement: warning  # advisory / warning / blocking
standards:
  naming:
    functions: "^[a-zA-Z][a-zA-Z0-9_]*$"  # allow camelCase
```
- Or use industry packs: push `shared/rules/banking.yaml` to the repo and set `config_path`

### Real-World Example: Scanning a Different Repo

- Installed on [ai-crowdsourcing-onboarding repo](https://github.com/mirzailhami/ai-crowdsourcing-onboarding)
- Copilot generated a LICENSE file with extra whitespace → bot flagged it instantly: [CopilotShield comment on license whitespace](https://github.com/mirzailhami/ai-crowdsourcing-onboarding/pull/1#issuecomment-3910894851)

## Contributing
- Contributions welcome! Fork → branch → PR.
- Please open issues for bugs or feature requests.

## License
MIT License — see [LICENSE](LICENSE) file for full text.
