import { Probot } from 'probot';
import { Octokit } from '@octokit/rest';
import fetch from 'node-fetch';

export = (app: Probot) => {
  app.log.info('Guardrails MVP Started');

  app.on('pull_request.opened', async (context: any) => {
    const pr = context.payload.pull_request;
    const owner = pr.head.repo.owner.login;
    const repo = pr.head.repo.name;
    const prNumber = pr.number;
    const sha = pr.head.sha;
    const commitMsg = pr.head.commit.message.toLowerCase();

    app.log.info(`Scanning PR #${prNumber}`);  // .info() call

    // Fetch diff
    const { data: diff } = await context.octokit.pulls.get({
      owner, repo, pull_number: prNumber, mediaType: { format: 'diff' }
    });

    // Fetch files
    const { data: fileList } = await context.octokit.pulls.listFiles({ owner, repo, pull_number: prNumber, per_page: 100 });
    const files = fileList.map((f: any) => f.filename);

    // Copilot heuristic
    const isCopilot = commitMsg.includes('copilot') || commitMsg.includes('ai-generated') || commitMsg.includes('copilot suggestion');

    // POST to backend
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const res = await fetch(`${backendUrl}/scan`, {
      method: 'POST' as const,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pr_id: `${owner}-${repo}-${prNumber}`,
        diff: diff,
        files,
        config_path: '.github/guardrails.yaml',
        is_copilot: isCopilot
      })
    });
    const results = await res.json() as any;

    const violations = results.violations || [];
    const policy = results.policy || 'warning';
    const total = results.total || 0;

    if (total > 0) {
      const table = `| Type | Description | Location | Severity | Copilot? |\n|------|-------------|----------|----------|----------|\n${violations.map((v: any) => `| ${v.type} | ${v.description} | ${v.location || 'N/A'} | ${v.severity || 'N/A'} | ${v.copilot_flag ? '🚨 Yes' : 'No'} |`).join('\n')}`;
      const body = `### Guardrails Scan: ${total} Issues 🚨\n**Policy**: ${policy.toUpperCase()}\n**Copilot Mode**: ${isCopilot ? 'Enabled (Stricter Checks)' : 'Off'}\n\n${table}\n\n${policy === 'blocking' ? '❌ Merge blocked—fix or /override.' : '⚠️ Review fixes.'}`;

      await context.octokit.issues.createComment(context.issue({ body }));

      const state = policy === 'blocking' ? 'failure' : 'success';
      const desc = isCopilot ? `${total} violations (AI-flagged)` : `${total} violations`;
      await context.octokit.repos.createCommitStatus({
        owner, repo, sha, state, context: 'Guardrails', 
        description: `${desc} (${policy})`,
        target_url: `${backendUrl}/docs`
      });
    } else {
      await context.octokit.issues.createComment(context.issue({ body: '### Guardrails: All Clear! ✅ Merge away.' }));
      await context.octokit.repos.createCommitStatus({
        owner, repo, sha, state: 'success', context: 'Guardrails', description: 'Passed'
      });
    }
  });

  // Override
  app.on('issue_comment.created', async (context: any) => {
    if (context.payload.comment.body.trim() === '/override') {
      const pr = context.payload.issue;
      await context.octokit.repos.createCommitStatus({
        owner: pr.repository.owner.login, repo: pr.repository.name, sha: pr.pull_request.head.sha,
        state: 'success', context: 'Guardrails', description: 'Overridden ⚠️'
      });
      await context.octokit.issues.createComment(context.issue({ body: 'Override approved—proceed with caution.' }));
    }
  });
};