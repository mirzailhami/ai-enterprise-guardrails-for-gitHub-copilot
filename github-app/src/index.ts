import { Probot } from "probot";
import fetch from "node-fetch";

export = (app: Probot) => {
  app.log.info("Guardrails MVP Started - App loaded!");

  app.on("pull_request.opened", async (context: any) => {
    app.log.info("pull_request.opened triggered!");
    await handlePR(context, app);
  });

  app.on("pull_request.reopened", async (context: any) => {
    app.log.info("pull_request.reopened triggered!");
    await handlePR(context, app);
  });

  app.on("pull_request.synchronize", async (context: any) => {
    await handlePR(context, app);
  });

  async function handlePR(context: any, app: Probot) {
    let configPath = ".github/guardrails.yaml"; // Default

    const pr = context.payload.pull_request;
    const owner = pr.head.repo.owner.login;
    const repo = pr.head.repo.name;
    const prNumber = pr.number;
    const sha = pr.head.sha;

    // repo-specific overrides
    if (
      repo.toLowerCase().includes("banking") ||
      repo.toLowerCase().includes("finance")
    ) {
      configPath = "shared/rules/banking.yaml";
    } else if (
      repo.toLowerCase().includes("health") ||
      repo.toLowerCase().includes("medical")
    ) {
      configPath = "shared/rules/healthcare.yaml";
    }

    app.log.info(`Scanning PR #${prNumber} in ${owner}/${repo}`);

    try {
      // Fetch diff
      const { data: diff } = await context.octokit.pulls.get({
        owner,
        repo,
        pull_number: prNumber,
        mediaType: { format: "diff" },
      });
      app.log.info("Diff fetched successfully");

      // Fetch changed files list
      const { data: fileList } = await context.octokit.pulls.listFiles({
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
            const { data: contentData } =
              await context.octokit.repos.getContent({
                owner,
                repo,
                path: file.filename,
                ref: sha,
              });
            const content = Buffer.from(contentData.content, "base64").toString(
              "utf-8"
            );
            // Skip binary-like content (contains null bytes)
            if (content.includes("\x00")) {
              app.log.warn(`Skipping binary-like file: ${file.filename}`);
              continue;
            }
            filesWithContent.push({ path: file.filename, content });
            app.log.info(
              `Fetched content for ${file.filename} (${content.length} chars)`
            );
          } catch (err) {
            app.log.warn(
              `Failed to fetch content for ${file.filename}: ${err}`
            );
          }
        }
      }
      app.log.info(`Files with content fetched: ${filesWithContent.length}`);

      // Fetch commit message
      let commitMsg = "";
      try {
        // Use PR head commit SHA explicitly
        const commitSha = pr.head.sha;
        const { data: commitData } = await context.octokit.repos.getCommit({
          owner,
          repo,
          ref: commitSha,
        });

        commitMsg = commitData?.commit?.message?.toLowerCase() || "";
        if (!commitMsg) {
          app.log.warn("Commit message was empty or missing in response");
        }
      } catch (err) {
        app.log.warn(`Failed to fetch commit message: ${err.message}`);
        if (err.response) {
          app.log.warn(
            `API response status: ${
              err.response.status
            }, data: ${JSON.stringify(err.response.data)}`
          );
        }
      }

      // Copilot detection: check commit message, PR author, branch name, and PR body
      const commitMsgHasCopilot =
        commitMsg.includes("copilot") ||
        commitMsg.includes("ai-generated") ||
        commitMsg.includes("copilot suggestion");

      // Check PR author login and type for Copilot-related accounts
      const prUser = pr.user || {};
      const authorLogin = prUser.login?.toLowerCase() || "";
      const authorType = prUser.type?.toLowerCase() || "";
      const authorIsCopilot =
        authorLogin === "copilot" ||
        authorLogin === "copilot-swe-agent" ||
        (authorType === "bot" && authorLogin.includes("copilot"));

      // Check if branch name has copilot/ prefix
      const branchName = pr.head?.ref?.toLowerCase() || "";
      const branchIsCopilot = branchName.startsWith("copilot/");

      // Check if PR body contains Copilot coding agent reference
      const prBody = pr.body?.toLowerCase() || "";
      const bodyHasCopilot = prBody.includes("copilot coding agent");

      const isCopilot =
        commitMsgHasCopilot ||
        authorIsCopilot ||
        branchIsCopilot ||
        bodyHasCopilot;
      app.log.info(`Copilot mode: ${isCopilot}`);

      // POST to backend
      const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
      app.log.info(`Sending to backend: ${backendUrl}/scan`);
      app.log.info(`API Key present: ${!!process.env.BACKEND_API_KEY}`);
      const res = await fetch(`${backendUrl}/scan`, {
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
      if (!res.ok) {
        const text = await res.text();
        app.log.warn(`Backend error body: ${text}`);
        throw new Error(`Backend ${res.status}: ${text}`);
      }
      const results = await res.json();

      const violations = results.violations || [];
      const policy = results.policy || "warning";
      const total = results.total || 0;
      app.log.info(`Scan results: ${total} violations, policy: ${policy}`);

      if (total > 0) {
        const table =
          `| Type | Description | Location | Severity | Copilot? | Details |\n` +
          `|------|-------------|----------|----------|----------|---------|\n` +
          violations
            .map((v: any) => {
              const type = v.type || v.issue || "ai_review";
              const fileInfo = v.file_path ? ` in ${v.file_path}` : "";
              const desc =
                (v.description || v.issue || "AI-detected issue") + fileInfo;
              const loc = v.location || "N/A";
              const sev = v.severity || "medium";
              const copilot = v.copilot_flag ? "🚨 Yes" : "No";

              // Details: show all AI fields
              const details = [];
              if (v.fix) details.push(`**Fix:** ${v.fix}`);
              if (v.explanation) details.push(`**Expl:** ${v.explanation}`);
              if (v.reference) details.push(`**Ref:** ${v.reference}`);
              const detailsText =
                details.length > 0
                  ? details.join("<br>")
                  : v.cwe || v.owasp
                  ? `${v.cwe || ""} ${v.owasp || ""}`.trim()
                  : "N/A";

              return `| ${type} | ${desc} | ${loc} | ${sev} | ${copilot} | ${detailsText} |`;
            })
            .join("\n");
        const body = `### Guardrails Scan: ${total} Issues 🚨\n**Policy**: ${policy.toUpperCase()}\n**Copilot Mode**: ${
          isCopilot ? "Enabled (Stricter Checks)" : "Off"
        }\n\n${table}\n\n${
          policy === "blocking"
            ? "❌ Merge blocked—fix or /override."
            : "⚠️ Review fixes."
        }`;

        await context.octokit.issues.createComment(context.issue({ body }));

        const state = policy === "blocking" ? "failure" : "success";
        const desc = isCopilot
          ? `${total} violations (AI-flagged)`
          : `${total} violations`;
        await context.octokit.repos.createCommitStatus({
          owner,
          repo,
          sha,
          state,
          context: "Guardrails",
          description: `${desc} (${policy})`,
          target_url: `${backendUrl}/docs`,
        });
        app.log.info("Status check set");
      } else {
        await context.octokit.issues.createComment(
          context.issue({ body: "### Guardrails: All Clear! ✅ Merge away." })
        );
        await context.octokit.repos.createCommitStatus({
          owner,
          repo,
          sha,
          state: "success",
          context: "Guardrails",
          description: "Passed",
        });
        app.log.info("Clear comment and status posted");
      }
    } catch (error) {
      app.log.error(`Error in PR handler: ${error.message}`);
      await context.octokit.issues.createComment(
        context.issue({ body: `### Guardrails Error: ${error.message}` })
      );
    }
  }

  app.on("issue_comment.created", async (context: any) => {
    const commentBody = context.payload.comment.body.trim();

    if (commentBody !== "/override") {
      return;
    }

    app.log.info("Override command received - processing!");

    try {
      const prNumber = context.payload.issue.number;
      const owner = context.payload.repository.owner.login;
      const repo = context.payload.repository.name;

      const { data: pr } = await context.octokit.pulls.get({
        owner,
        repo,
        pull_number: prNumber,
      });
      const sha = pr.head.sha;
      app.log.info(`Fetched current PR head SHA: ${sha}`);

      await context.octokit.repos.createCommitStatus({
        owner,
        repo,
        sha,
        state: "success",
        context: "Guardrails",
        description: "Overridden ⚠️",
      });
      app.log.info("Status overridden to success");

      await context.octokit.issues.createComment(
        context.issue({
          body: "Override approved—proceed with caution.",
        })
      );
      app.log.info("Override reply comment posted");
    } catch (err) {
      app.log.error(`Override failed: ${err.message}`);
      if (err.response) {
        app.log.error(`API details: ${JSON.stringify(err.response.data)}`);
      }
      // Still post reply even if status fails
      await context.octokit.issues.createComment(
        context.issue({
          body: "Override approved (status update failed, but proceed with caution).",
        })
      );
    }
  });
};
