# Portable Skill API reference

The Skill directory needs only SKILL.md, scripts/learning_client.py and this file.
The application backend is a separate prerequisite; no developer's absolute path is required.
Python 3.12 and a running loopback service are sufficient for the client. It disables environment proxies and rejects redirects/remote base URLs.

Run `python scripts/learning_client.py --help` for supported operations. Paths below are relative to this installed Skill folder, not the product checkout.

```sh
python scripts/learning_client.py capabilities
python scripts/learning_client.py learn --file lesson.pdf --unit-index 1 --question "解释这里的梯度下降" --repo owner/repo --network-authorized
python scripts/learning_client.py learn --file lesson.md --question "解释这个知识点" --source-mode local_authorized --local-handle AUTHORIZED_HANDLE
python scripts/learning_client.py explain --request-json followup.json
python scripts/learning_client.py notes --query "梯度下降"
```

`--network-authorized` records an authorization already given by the user for those repositories. Public search additionally needs `--source-mode public_search` and repeated `--approved-term` values explicitly approved by the user; if the plan proposes a new term, the server stops before sending it.
`--selected-text` locates a unique substring in server-returned blocks; ambiguous selection returns SELECTION_MISMATCH. Office/PDF parsing belongs to the installed Document Provider, not this script.

For follow-up, keep the session_id, context_revision, scope and previous explanation_id from the original result:

```json
{
  "session_id": "RETURNED_SESSION_ID",
  "context_revision": 1,
  "question": "这个实现的边界条件是什么？",
  "level": "Engineering",
  "continue_from": "RETURNED_EXPLANATION_ID",
  "scope": {
    "source_mode": "specified_public",
    "repository_allowlist": ["owner/repo"],
    "network_authorized": true
  }
}
```

Do not fabricate IDs. NEEDS_SOURCE_SELECTION returns real server query_id/candidates; explain again with those candidate_ids, the same scope/session/context_revision and a fresh request_id. Comparison uses compare=true and scope containing both chosen repositories; at least two independently verified sources are required.

Saving needs an explicit separate user action. Reuse one idempotency key for retries of that exact save:

```sh
python scripts/learning_client.py save --session-id RETURNED_SESSION_ID --explanation-id RETURNED_EXPLANATION_ID --idempotency-key UNIQUE_SAVE_ID --title "我的笔记" --text "我的理解" --confirm
python scripts/learning_client.py edit-note --note-id RETURNED_NOTE_ID --revision 1 --title "新的标题" --text "更新我的理解"
python scripts/learning_client.py export-note --note-id RETURNED_NOTE_ID --format markdown
python scripts/learning_client.py delete-note --note-id RETURNED_NOTE_ID --revision 2 --confirm
```

Export writes UTF-8 content to stdout. Editing changes only personal text and creates a revision. Confirm deletion of the exact note; no source file or repository is deleted. A save retry after deletion returns NOTE_NOT_FOUND and cannot recreate it.

Error JSON has code/user_message/http_status and a nonzero process exit. Never turn MODULE_NOT_DELIVERED, MODEL_NOT_CONFIGURED, NETWORK_NOT_AUTHORIZED, QUERY_TERMS_NOT_APPROVED, SOURCE_MISMATCH, CITATION_INVALID or CANCELLED into a successful explanation. Do not fill gaps with invented repositories, fixed Fixture answers or an unapproved cloud model.

Install by extracting the package into a supported host's configured skill directory, preserving the concept-to-code-learning folder. The host needs permission to run Python and reach this local service. Explicitly invoke `$concept-to-code-learning` where supported; automatic selection differs by host and is not guaranteed. For an API-only host, invoke the same client with its execution tool. This package does not install the backend, Python, models or system software.

Independent smoke covers a controlled local HTTP service with labelled provider doubles. A real-document + real-source + real-model acceptance remains separately required. No host trigger or competition qualification is claimed from ZIP validation alone.
