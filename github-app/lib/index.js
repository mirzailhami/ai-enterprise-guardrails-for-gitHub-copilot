"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
const node_fetch_1 = __importDefault(require("node-fetch"));
module.exports = (app) => {
    app.log.info("Guardrails MVP Started - App loaded!");
    app.on("pull_request.opened", (context) => __awaiter(void 0, void 0, void 0, function* () {
        app.log.info("pull_request.opened triggered!");
        yield handlePR(context, app);
    }));
    app.on("pull_request.reopened", (context) => __awaiter(void 0, void 0, void 0, function* () {
        app.log.info("pull_request.reopened triggered!");
        yield handlePR(context, app);
    }));
    app.on("pull_request.synchronize", (context) => __awaiter(void 0, void 0, void 0, function* () {
        yield handlePR(context, app);
    }));
    function handlePR(context, app) {
        return __awaiter(this, void 0, void 0, function* () {
            var _a, _b, _c, _d, _e, _f, _g, _h, _j;
            let configPath = ".github/guardrails.yaml"; // Default
            const pr = context.payload.pull_request;
            const owner = pr.head.repo.owner.login;
            const repo = pr.head.repo.name;
            const prNumber = pr.number;
            const sha = pr.head.sha;
            // repo-specific overrides
            if (repo.toLowerCase().includes("banking") ||
                repo.toLowerCase().includes("finance")) {
                configPath = "shared/rules/banking.yaml";
            }
            else if (repo.toLowerCase().includes("health") ||
                repo.toLowerCase().includes("medical")) {
                configPath = "shared/rules/healthcare.yaml";
            }
            app.log.info(`Scanning PR #${prNumber} in ${owner}/${repo}`);
            try {
                // Fetch diff
                const { data: diff } = yield context.octokit.pulls.get({
                    owner,
                    repo,
                    pull_number: prNumber,
                    mediaType: { format: "diff" },
                });
                app.log.info("Diff fetched successfully");
                // Fetch changed files list
                const { data: fileList } = yield context.octokit.pulls.listFiles({
                    owner,
                    repo,
                    pull_number: prNumber,
                    per_page: 100,
                });
                // Fetch actual content for each file
                const filesWithContent = [];
                for (const file of fileList) {
                    if (file.status === "added" || file.status === "modified") {
                        try {
                            const { data: contentData } = yield context.octokit.repos.getContent({
                                owner,
                                repo,
                                path: file.filename,
                                ref: sha,
                            });
                            const content = Buffer.from(contentData.content, "base64").toString("utf-8");
                            // Skip binary-like content (contains null bytes)
                            if (content.includes("\x00")) {
                                app.log.warn(`Skipping binary-like file: ${file.filename}`);
                                continue;
                            }
                            filesWithContent.push({ path: file.filename, content });
                            app.log.info(`Fetched content for ${file.filename} (${content.length} chars)`);
                        }
                        catch (err) {
                            app.log.warn(`Failed to fetch content for ${file.filename}: ${err}`);
                        }
                    }
                }
                app.log.info(`Files with content fetched: ${filesWithContent.length}`);
                // Fetch commit message
                let commitMsg = "";
                try {
                    // Use PR head commit SHA explicitly
                    const commitSha = pr.head.sha;
                    const { data: commitData } = yield context.octokit.repos.getCommit({
                        owner,
                        repo,
                        ref: commitSha,
                    });
                    commitMsg = ((_b = (_a = commitData === null || commitData === void 0 ? void 0 : commitData.commit) === null || _a === void 0 ? void 0 : _a.message) === null || _b === void 0 ? void 0 : _b.toLowerCase()) || "";
                    if (!commitMsg) {
                        app.log.warn("Commit message was empty or missing in response");
                    }
                }
                catch (err) {
                    app.log.warn(`Failed to fetch commit message: ${err.message}`);
                    if (err.response) {
                        app.log.warn(`API response status: ${err.response.status}, data: ${JSON.stringify(err.response.data)}`);
                    }
                }
                // Copilot detection: check commit message, PR author, branch name, and PR body
                const commitMsgHasCopilot = commitMsg.includes("copilot") ||
                    commitMsg.includes("ai-generated") ||
                    commitMsg.includes("copilot suggestion");
                // Check PR author login and type for Copilot-related accounts
                const authorLogin = ((_d = (_c = pr.user) === null || _c === void 0 ? void 0 : _c.login) === null || _d === void 0 ? void 0 : _d.toLowerCase()) || "";
                const authorType = ((_f = (_e = pr.user) === null || _e === void 0 ? void 0 : _e.type) === null || _f === void 0 ? void 0 : _f.toLowerCase()) || "";
                const authorIsCopilot = authorLogin === "copilot" ||
                    authorLogin === "copilot-swe-agent" ||
                    (authorLogin.includes("copilot") && authorType === "bot");
                // Check if branch name has copilot/ prefix
                const branchName = ((_h = (_g = pr.head) === null || _g === void 0 ? void 0 : _g.ref) === null || _h === void 0 ? void 0 : _h.toLowerCase()) || "";
                const branchIsCopilot = branchName.startsWith("copilot/");
                // Check if PR body contains Copilot agent tips
                const prBody = ((_j = pr.body) === null || _j === void 0 ? void 0 : _j.toLowerCase()) || "";
                const bodyHasCopilot = prBody.includes("copilot coding agent");
                const isCopilot = commitMsgHasCopilot ||
                    authorIsCopilot ||
                    branchIsCopilot ||
                    bodyHasCopilot;
                app.log.info(`Copilot mode: ${isCopilot}`);
                // POST to backend
                const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
                const res = yield (0, node_fetch_1.default)(`${backendUrl}/scan`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-API-Key": process.env.BACKEND_API_KEY || "",
                    },
                    body: JSON.stringify({
                        pr_id: `${owner}-${repo}-${prNumber}`,
                        diff: diff,
                        files: filesWithContent,
                        config_path: configPath, // ".github/guardrails.yaml",
                        is_copilot: isCopilot,
                    }),
                });
                app.log.info(`Backend response status: ${res.status}`);
                const results = yield res.json();
                const violations = results.violations || [];
                const policy = results.policy || "warning";
                const total = results.total || 0;
                app.log.info(`Scan results: ${total} violations, policy: ${policy}`);
                if (total > 0) {
                    const table = `| Type | Description | Location | Severity | Copilot? | Details |\n` +
                        `|------|-------------|----------|----------|----------|---------|\n` +
                        violations
                            .map((v) => {
                            const type = v.type || v.issue || "ai_review";
                            const fileInfo = v.file_path ? ` in ${v.file_path}` : "";
                            const desc = (v.description || v.issue || "AI-detected issue") + fileInfo;
                            const loc = v.location || "N/A";
                            const sev = v.severity || "medium";
                            const copilot = v.copilot_flag ? "🚨 Yes" : "No";
                            // Details: show all AI fields
                            const details = [];
                            if (v.fix)
                                details.push(`**Fix:** ${v.fix}`);
                            if (v.explanation)
                                details.push(`**Expl:** ${v.explanation}`);
                            if (v.reference)
                                details.push(`**Ref:** ${v.reference}`);
                            const detailsText = details.length > 0
                                ? details.join("<br>")
                                : v.cwe || v.owasp
                                    ? `${v.cwe || ""} ${v.owasp || ""}`.trim()
                                    : "N/A";
                            return `| ${type} | ${desc} | ${loc} | ${sev} | ${copilot} | ${detailsText} |`;
                        })
                            .join("\n");
                    const body = `### Guardrails Scan: ${total} Issues 🚨\n**Policy**: ${policy.toUpperCase()}\n**Copilot Mode**: ${isCopilot ? "Enabled (Stricter Checks)" : "Off"}\n\n${table}\n\n${policy === "blocking"
                        ? "❌ Merge blocked—fix or /override."
                        : "⚠️ Review fixes."}`;
                    yield context.octokit.issues.createComment(context.issue({ body }));
                    const state = policy === "blocking" ? "failure" : "success";
                    const desc = isCopilot
                        ? `${total} violations (AI-flagged)`
                        : `${total} violations`;
                    yield context.octokit.repos.createCommitStatus({
                        owner,
                        repo,
                        sha,
                        state,
                        context: "Guardrails",
                        description: `${desc} (${policy})`,
                        target_url: `${backendUrl}/docs`,
                    });
                    app.log.info("Status check set");
                }
                else {
                    yield context.octokit.issues.createComment(context.issue({ body: "### Guardrails: All Clear! ✅ Merge away." }));
                    yield context.octokit.repos.createCommitStatus({
                        owner,
                        repo,
                        sha,
                        state: "success",
                        context: "Guardrails",
                        description: "Passed",
                    });
                    app.log.info("Clear comment and status posted");
                }
            }
            catch (error) {
                app.log.error(`Error in PR handler: ${error.message}`);
                yield context.octokit.issues.createComment(context.issue({ body: `### Guardrails Error: ${error.message}` }));
            }
        });
    }
    app.on("issue_comment.created", (context) => __awaiter(void 0, void 0, void 0, function* () {
        const commentBody = context.payload.comment.body.trim();
        if (commentBody !== "/override") {
            return;
        }
        app.log.info("Override command received - processing!");
        try {
            const prNumber = context.payload.issue.number;
            const owner = context.payload.repository.owner.login;
            const repo = context.payload.repository.name;
            const { data: pr } = yield context.octokit.pulls.get({
                owner,
                repo,
                pull_number: prNumber,
            });
            const sha = pr.head.sha;
            app.log.info(`Fetched current PR head SHA: ${sha}`);
            yield context.octokit.repos.createCommitStatus({
                owner,
                repo,
                sha,
                state: "success",
                context: "Guardrails",
                description: "Overridden ⚠️",
            });
            app.log.info("Status overridden to success");
            yield context.octokit.issues.createComment(context.issue({
                body: "Override approved—proceed with caution.",
            }));
            app.log.info("Override reply comment posted");
        }
        catch (err) {
            app.log.error(`Override failed: ${err.message}`);
            if (err.response) {
                app.log.error(`API details: ${JSON.stringify(err.response.data)}`);
            }
            // Still post reply even if status fails
            yield context.octokit.issues.createComment(context.issue({
                body: "Override approved (status update failed, but proceed with caution).",
            }));
        }
    }));
};
