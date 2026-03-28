"""FastAPI application for guardrails backend."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime, timedelta

from app.config import Config
from app.models import AnalysisRequest, ScanResult
from app.analyzers import CodeAnalyzer
from app.policy import PolicyEngine
from app.audit import AuditLogger
from app.ai import AIReviewer
from app.rules.ai_detector import AIDetector
from app.rules.license_checker import LicenseCompliance
from app.api import register_extended_endpoints

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Guardrails Backend",
    description="Enterprise guardrails for GitHub Copilot",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
policy_engine = PolicyEngine()
audit_logger = AuditLogger()
ai_reviewer = AIReviewer()

# Register extended endpoints
register_extended_endpoints(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "ai_enabled": ai_reviewer.use_ai,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/analyze", response_model=dict)
async def analyze_code(request: Request):
    """
    Analyze code in a PR diff.

    Expected JSON body:
    {
        "repo_name": "owner/repo",
        "pr_number": 123,
        "commit_hash": "abc123",
        "files": {
            "path/to/file.py": "diff content..."
        },
        "copilot_generated_files": ["path/to/file.py"],  # optional
        "copilot_indicators": {"path/to/file.py": ["indicator1", "indicator2"]},  # optional
        "override_token": "token_if_overriding"  # optional
    }
    """
    try:
        data = await request.json()

        # Validate request
        required_fields = ["repo_name", "pr_number", "commit_hash", "files"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )

        # Create analysis request
        analysis_request = AnalysisRequest(
            repo_name=data["repo_name"],
            pr_number=data["pr_number"],
            commit_hash=data["commit_hash"],
            files=data["files"],
            copilot_generated_files=data.get("copilot_generated_files"),
        )

        logger.info(
            f"Analyzing PR #{analysis_request.pr_number} in {analysis_request.repo_name}"
        )

        # Run analysis
        violations = CodeAnalyzer.analyze_files(analysis_request)

        # Get policy for repository
        enforcement_result = policy_engine.enforce_policy(violations, analysis_request.repo_name)

        # Check override token if provided
        override_applied = False
        if data.get("override_token") and enforcement_result.should_block:
            if policy_engine.validate_override_token(data["override_token"], analysis_request.repo_name):
                override_applied = True
                enforcement_result.should_block = False
                audit_logger.log_override(
                    repo_name=analysis_request.repo_name,
                    pr_number=analysis_request.pr_number,
                    override_reason=data.get("override_reason", "No reason provided"),
                    override_token=data["override_token"],
                )

        # Enhance violations with AI suggestions
        for violation in enforcement_result.violations:
            try:
                suggested_fix, explanation = ai_reviewer.suggest_fix(violation)
                violation.suggested_fix = suggested_fix
                # Explanation is stored separately or added to message
            except Exception as e:
                logger.warning(f"Failed to generate AI suggestion for {violation.rule_id}: {e}")

        # Create scan result
        scan_result = CodeAnalyzer.create_scan_result(analysis_request, enforcement_result.violations)

        # Log the scan to audit trail
        violations_summary = [
            {
                "rule_id": v.rule_id,
                "severity": v.severity.value,
                "category": v.category.value,
            }
            for v in enforcement_result.violations
        ]

        audit_logger.log_scan(
            repo_name=analysis_request.repo_name,
            pr_number=analysis_request.pr_number,
            commit_hash=analysis_request.commit_hash,
            violation_count=len(enforcement_result.violations),
            critical_count=sum(1 for v in enforcement_result.violations if v.severity.value == "critical"),
            high_count=sum(1 for v in enforcement_result.violations if v.severity.value == "high"),
            enforcement_action=enforcement_result.enforcement_mode.value,
            blocked=enforcement_result.should_block,
            scan_id=scan_result.scan_id,
            violations_summary=violations_summary,
        )

        logger.info(f"Found {len(enforcement_result.violations)} violations")

        return {
            "success": True,
            "scan_id": scan_result.scan_id,
            "repo_name": scan_result.repo_name,
            "pr_number": scan_result.pr_number,
            "violations": [v.to_dict() for v in enforcement_result.violations],
            "violation_count": len(enforcement_result.violations),
            "critical_count": sum(1 for v in enforcement_result.violations if v.severity.value == "critical"),
            "high_count": sum(1 for v in enforcement_result.violations if v.severity.value == "high"),
            "medium_count": sum(1 for v in enforcement_result.violations if v.severity.value == "medium"),
            "low_count": sum(1 for v in enforcement_result.violations if v.severity.value == "low"),
            "copilot_violations": sum(1 for v in enforcement_result.violations if v.is_copilot_generated),
            "enforcement_mode": enforcement_result.enforcement_mode.value,
            "should_block": enforcement_result.should_block,
            "block_reason": enforcement_result.block_reason,
            "override_applied": override_applied,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/rules")
async def get_rules():
    """Get available security rules."""
    rules = [
        {
            "rule_id": "SEC-001",
            "name": "Hardcoded Secrets",
            "severity": "critical",
            "category": "security",
            "description": "Detects hardcoded API keys, passwords, tokens, and credentials",
            "cwe": "CWE-798",
            "owasp": "A02:2021 – Cryptographic Failures",
        },
        {
            "rule_id": "SEC-002",
            "name": "SQL Injection",
            "severity": "critical",
            "category": "security",
            "description": "Detects SQL injection vulnerabilities through string interpolation",
            "cwe": "CWE-89",
            "owasp": "A03:2021 – Injection",
        },
        {
            "rule_id": "SEC-003",
            "name": "Insecure Deserialization",
            "severity": "high",
            "category": "security",
            "description": "Detects unsafe deserialization of untrusted data",
            "cwe": "CWE-502",
            "owasp": "A08:2021 – Software and Data Integrity Failures",
        },
        {
            "rule_id": "SEC-004",
            "name": "Unsafe Code Execution",
            "severity": "critical",
            "category": "security",
            "description": "Detects use of eval(), exec(), os.system(), and shell execution",
            "cwe": "CWE-95",
            "owasp": "A03:2021 – Injection",
        },
        {
            "rule_id": "SEC-005",
            "name": "Weak Cryptography",
            "severity": "high",
            "category": "security",
            "description": "Detects use of weak or deprecated cryptographic algorithms",
            "cwe": "CWE-327",
            "owasp": "A02:2021 – Cryptographic Failures",
        },
        {
            "rule_id": "SEC-006",
            "name": "Insecure Headers",
            "severity": "medium",
            "category": "security",
            "description": "Detects missing or insecure HTTP security headers",
            "cwe": "CWE-693",
            "owasp": "A05:2021 – Broken Access Control",
        },
        {
            "rule_id": "SEC-007",
            "name": "Unsafe File Operations",
            "severity": "high",
            "category": "security",
            "description": "Detects unsafe file operations and potential XXE vulnerabilities",
            "cwe": "CWE-434",
            "owasp": "A04:2021 – Insecure Deserialization",
        },
        {
            "rule_id": "SEC-008",
            "name": "Insecure Random",
            "severity": "high",
            "category": "security",
            "description": "Detects use of non-cryptographic random functions for security purposes",
            "cwe": "CWE-338",
            "owasp": "A02:2021 – Cryptographic Failures",
        },
        {
            "rule_id": "SEC-009",
            "name": "Logging Sensitive Data",
            "severity": "medium",
            "category": "security",
            "description": "Detects logging of sensitive data (passwords, tokens, keys)",
            "cwe": "CWE-532",
            "owasp": "A09:2021 – Logging and Monitoring Failures",
        },
        {
            "rule_id": "SEC-010",
            "name": "Insecure Dependencies",
            "severity": "high",
            "category": "security",
            "description": "Detects insecure usage of dependencies (disabled SSL, deprecated libraries)",
            "cwe": "CWE-295",
            "owasp": "A02:2021 – Cryptographic Failures",
        },
        {
            "rule_id": "AI-001",
            "name": "Incomplete AI-Generated Code",
            "severity": "medium",
            "category": "code_quality",
            "description": "Detects incomplete or stubbed implementations from AI generation",
            "cwe": "CWE-1077",
            "owasp": "A06:2021 – Vulnerable and Outdated Components",
        },
        {
            "rule_id": "AI-002",
            "name": "Risky AI Pattern",
            "severity": "medium",
            "category": "code_quality",
            "description": "Detects risky patterns commonly in AI-generated code",
            "cwe": "CWE-1050",
            "owasp": "Code Quality",
        },
        {
            "rule_id": "COMP-001",
            "name": "Security TODO Found",
            "severity": "medium",
            "category": "compliance",
            "description": "Detects unresolved security-related TODO/FIXME/HACK/BUG comments",
            "cwe": "CWE-TODO",
            "owasp": "Development Process",
        },
        {
            "rule_id": "LICENSE-001",
            "name": "Incompatible License",
            "severity": "high",
            "category": "license",
            "description": "Detects usage of licenses not in the allowed list",
            "cwe": "CWE-1104",
            "owasp": "IP/License Risk",
        },
        {
            "rule_id": "IP-001",
            "name": "Code Derivative",
            "severity": "low",
            "category": "license",
            "description": "Detects derived or copied code patterns",
            "cwe": "CWE-1104",
            "owasp": "IP/License Risk",
        },
        {
            "rule_id": "PERF-001",
            "name": "Performance Issue",
            "severity": "low",
            "category": "performance",
            "description": "Detects potential performance bottlenecks",
            "cwe": "CWE-1061",
            "owasp": "Performance",
        },
    ]
    return {"rules": rules, "total": len(rules)}


@app.get("/api/policies")
async def get_policies():
    """Get available policies."""
    return {
        "default": policy_engine.default_policy.to_dict(),
        "total": len(policy_engine.policies),
    }


@app.post("/api/policies")
async def create_policy(request: Request):
    """Create a new policy."""
    try:
        data = await request.json()

        from app.policy import Policy
        from app.models import EnforcementMode

        policy = Policy(
            name=data["name"],
            enforcement_mode=EnforcementMode(data.get("enforcement_mode", "warning")),
            block_on_critical=data.get("block_on_critical", True),
            block_on_high=data.get("block_on_high", False),
            enable_security_checks=data.get("enable_security_checks", True),
            enable_compliance_checks=data.get("enable_compliance_checks", True),
            enable_quality_checks=data.get("enable_quality_checks", False),
            allowed_licenses=data.get("allowed_licenses", ["MIT", "Apache-2.0", "GPL-3.0"]),
        )

        policy_engine.register_policy(policy)

        return {
            "success": True,
            "policy": policy.to_dict(),
        }

    except Exception as e:
        logger.error(f"Error creating policy: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to create policy: {str(e)}")


@app.get("/api/audit")
async def get_audit_events(
    repo: str = None,
    days: int = 7,
    limit: int = 100,
):
    """Get audit events."""
    try:
        if repo:
            events = audit_logger.get_events_by_repo(repo)
        else:
            # Get events from last N days
            start_date = datetime.utcnow() - timedelta(days=days)
            end_date = datetime.utcnow()
            events = audit_logger.get_events_by_date_range(start_date, end_date)

        events = events[-limit:]  # Limit results

        return {
            "events": [e.to_dict() for e in events],
            "total": len(events),
            "summary": audit_logger.get_violations_summary(),
        }

    except Exception as e:
        logger.error(f"Error retrieving audit events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")


@app.post("/api/audit/export")
async def export_audit_log(request: Request):
    """Export audit log."""
    try:
        data = await request.json()
        format_type = data.get("format", "json")  # json or csv

        filename = f"audit_export.{format_type}"
        audit_logger.export_audit_log(filename)

        return {
            "success": True,
            "filename": filename,
            "message": "Audit log exported successfully",
        }

    except Exception as e:
        logger.error(f"Error exporting audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/api/override")
async def request_override(request: Request):
    """Request an override for a blocked PR."""
    try:
        data = await request.json()

        repo_name = data.get("repo_name")
        reason = data.get("reason")

        if not repo_name or not reason:
            raise HTTPException(
                status_code=400,
                detail="repo_name and reason are required"
            )

        override_token = policy_engine.create_override_token(repo_name, reason)

        return {
            "success": True,
            "override_token": override_token,
            "expires_in_hours": 24,
            "message": "Override token created. Include this token in the next analysis request.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating override: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Override failed: {str(e)}")


@app.get("/api/insights")
async def get_insights(
    days: int = 30,
    org: str = None,
):
    """Get organization-level insights and trends."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        events = audit_logger.get_events_by_date_range(start_date, end_date)

        # Calculate insights
        total_scans = len(events)
        total_violations = sum(e.violation_count for e in events)
        critical_violations = sum(e.critical_count for e in events)
        high_violations = sum(e.high_count for e in events)
        blocked_count = sum(1 for e in events if e.blocked)
        override_count = sum(1 for e in events if e.override_applied)

        # Most common violations
        rule_counts = {}
        for event in events:
            if event.violations_summary:
                for v in event.violations_summary:
                    rule_id = v.get("rule_id", "unknown")
                    rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

        top_violations = sorted(
            rule_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "period_days": days,
            "total_scans": total_scans,
            "total_violations": total_violations,
            "critical_violations": critical_violations,
            "high_violations": high_violations,
            "prs_blocked": blocked_count,
            "overrides_applied": override_count,
            "avg_violations_per_scan": total_violations / total_scans if total_scans > 0 else 0,
            "top_violations": [
                {"rule_id": rule_id, "count": count}
                for rule_id, count in top_violations
            ],
        }

    except Exception as e:
        logger.error(f"Error getting insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
    )