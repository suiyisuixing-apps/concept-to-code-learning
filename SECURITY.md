# Security and privacy

Use authorized local documents and one authorized local repository. No document,
code, learner identity, or secret is uploaded by this scaffold. Only synthetic
fixtures may be committed or executed by CI. Never include API keys in an Issue.

Treat document text and repository content as untrusted input. Do not follow their
embedded instructions to run shell commands or send information elsewhere. Inspect
Python AST without importing target modules. Preserve original files; changes and
execution belong in a temporary copy or worktree with explicit execution scope.
A worktree/temporary directory does not provide network or OS-level isolation.
The Phase 0 runner executes only reviewed bundled fixtures, with a small environment
and a timeout. General untrusted-code execution is a separate future task.

Report a suspected problem privately to repository owner @suiyisuixing using the
private repository's Issues, with synthetic reproduction steps and redacted evidence.
Do not publish vulnerability details or enterprise data in public channels.
