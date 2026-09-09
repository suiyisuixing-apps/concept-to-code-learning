"""Declared policy checks only; live GitHub verification is separate evidence."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_declared_main_protection_preserves_independent_quality_gate():
    policy = json.loads(read("docs/governance/main-protection.json"))
    classic = policy["classic"]
    reviews = classic["required_pull_request_reviews"]
    assert reviews["required_approving_review_count"] == 0
    assert not reviews["require_code_owner_reviews"]
    assert not reviews["require_last_push_approval"]
    assert not reviews["dismiss_stale_reviews"]
    assert not reviews.get("bypass_pull_request_allowances")
    assert classic["enforce_admins"]["enabled"]
    assert classic["required_status_checks"]["strict"]
    assert classic["required_status_checks"]["checks"] == [
        {"context": "phase0-checks", "app_id": 15368}
    ]
    for key in ("allow_force_pushes", "allow_deletions", "required_conversation_resolution"):
        assert not classic[key]["enabled"]


def test_declared_owner_restriction_cannot_be_confused_with_ci_enforcement():
    policy = json.loads(read("docs/governance/main-protection.json"))
    ruleset = policy["ruleset"]
    assert policy["scope"] == "declared configuration, not live API validation"
    assert policy["lead"] == "suiyisuixing"
    assert ruleset["enforcement"] == "active"
    assert "refs/heads/main" in ruleset["conditions"]["ref_name"]["include"]
    assert not ruleset["conditions"]["ref_name"]["exclude"]
    assert ruleset["bypass_actors"] == [
        {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
    ]
    rules = {rule["type"]: rule for rule in ruleset["rules"]}
    assert {"update", "deletion", "non_fast_forward", "pull_request",
            "required_status_checks"} <= rules.keys()
    reviews = rules["pull_request"]["parameters"]
    assert reviews["required_approving_review_count"] == 0
    for key in ("require_code_owner_review", "require_last_push_approval",
                "dismiss_stale_reviews_on_push", "required_review_thread_resolution"):
        assert not reviews[key]
    assert not reviews.get("required_reviewers")
    status = rules["required_status_checks"]["parameters"]
    assert status["strict_required_status_checks_policy"]
    assert status["required_status_checks"] == [
        {"context": "phase0-checks", "integration_id": 15368}
    ]
    # A bypassed ruleset alone does not preserve the administrator's CI gate.
    assert policy["classic"]["enforce_admins"]["enabled"]


def test_codeowners_only_contains_existing_paths_and_lead_on_every_rule():
    for line in read("CODEOWNERS").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        path, *owners = line.split()
        assert "@suiyisuixing" in owners
        assert path == "*" or (ROOT / path.lstrip("/")).exists()


@pytest.mark.parametrize("role", ["document-workspace", "github-intelligence", "tutor-evaluation"])
def test_member_prompts_leave_merge_decision_with_lead(role):
    text = read(f"docs/codex-prompts/{role}.md")
    assert "成员不得合并任何 PR" in text
    assert "@suiyisuixing 最终审核" in text
    assert "lead-review:pending" in text
    assert "不得绕过 CI" in text
    assert "Fixture" in text and "无自动云回退" in text and "零新付费" in text


def test_lead_prompt_requires_human_decision_and_exact_head_checks():
    text = read("docs/codex-prompts/lead-integration.md")
    for term in ("自行合并", "无需外部批准", "人工检查关键文件", "Codex 只读差异审计",
                 "phase0-checks", "P0/P1", "Codex 不代填人工检查", "Fixture", "零新付费"):
        assert term in text


def test_active_docs_do_not_restore_mandatory_peer_approval():
    paths = ["AGENTS.md", "CONTRIBUTING.md", "README.md", "SKILL.md",
             ".github/pull_request_template.md", "docs/roles-and-ownership.md",
             "docs/roadmap.md", "docs/sprint-1-first-real-vertical-slice.md",
             "docs/sprint-1-contract-review.md", "docs/api.md"]
    paths += [str(path.relative_to(ROOT)) for path in (ROOT / "docs/codex-prompts").glob("*.md")]
    for path in paths:
        text = read(path)
        for obsolete in ("Never approve or merge your own pull request",
                         "至少 1 个其他成员批准", "他人审核并合并后成为团队共同基线",
                         "至少一名真实其他成员的批准", "至少一名其他已接受邀请的真实队员审核",
                         "请求有 Write 权限的另一名真实成员审核",
                         "one actual other member's approval"):
            assert obsolete not in text, (path, obsolete)


def test_pr_template_and_agent_rules_keep_evidence_and_safety_boundaries():
    template = read(".github/pull_request_template.md")
    for field in ("Lead PR", "Team member PR", "LEAD_REVIEW_PENDING", "LEAD_APPROVED",
                  "LEAD_CHANGES_REQUESTED", "LEAD_DEFERRED", "已人工检查关键文件",
                  "Required CI", "Fixture", "公共 Schema"):
        assert field in template
    agents = read("AGENTS.md")
    for rule in ("Only @suiyisuixing may merge into main", "Never push directly to main",
                 "No pull request may merge with failed required checks",
                 "Fixtures must remain visibly labelled", "No automatic cloud fallback",
                 "Never invent repositories, commits, paths, symbols, lines or licenses",
                 "No force push or history rewriting", "zero new paid services"):
        assert rule in agents
