"""Offline exports use the saved version even if the original provider disappears."""

import html
import json
import re
from urllib.parse import quote

from concept_to_code_learning.full_contracts.models import SavedNote


def export_note(note: SavedNote, format: str) -> tuple[str, str]:
    if format == "json":
        return json.dumps(note.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", "application/json"
    if format != "markdown":
        raise ValueError("Supported formats: markdown, json")
    esc = html.escape
    lines = [f"# {esc(note.title)}", "", esc(note.user_text), "",
             f"修订：{note.revision} · 创建：{note.created_at.isoformat()} · 更新：{note.updated_at.isoformat()}",
             f"模式：{note.mode} · 快照 SHA-256：{note.snapshot_sha256}", "", "## 讲解快照", ""]
    for section in note.explanation_snapshot.answer_sections:
        lines += [f"### {esc(section.title)}", "", esc(section.text), ""]
    context = note.document_snapshot
    lines += ["## 文档来源", "", f"{esc(context.file_name)} · {context.unit_locator.unit_type} "
              f"{context.unit_locator.index} · 文档修订 {context.document_revision}",
              f"原文件 SHA-256：{context.original_sha256}", ""]
    if context.code_location:
        location = context.code_location
        lines += [f"仓库：{esc(location.repository)} · Commit：{location.commit_sha}",
                  f"文件：{esc(location.file_path)} · Git blob：{location.blob_sha}", ""]
    for citation in note.explanation_snapshot.document_citations:
        block = next((b for b in context.relevant_context_blocks if b.block_id == citation.block_id), None)
        if block and block.code_location:
            location = block.code_location
            start = location.line_start + block.text[:block.text.index(citation.quote)].count("\n")
            end = start + citation.quote.count("\n")
            link = f"https://github.com/{location.repository}/blob/{location.commit_sha}/{quote(location.file_path, safe='/')}#L{start}-L{max(start, end)}"
            lines += [f"[源文件 {esc(location.file_path)} L{start}–{max(start, end)}]({link})", ""]
            for license_file in (block.code_license.files if block.code_license else []):
                lines += [f"许可：{esc(license_file.identifier or '未识别')} · {esc(license_file.path)} · {license_file.content_sha256}",
                          f"[固定版本许可]({license_file.permalink})", ""]
        lines += [f"块 {esc(citation.block_id)} · {citation.quote_sha256}", "", esc(citation.quote), ""]
    lines += ["## 代码来源快照", ""]
    for source in note.code_evidence_snapshot:
        label = (source.repository_owner + "/" + source.repository_name) if source.repository_url else (
            "已授权本地仓库 " + source.local_handle)
        lines += [f"### {esc(label)}", "", f"{esc(source.file_path)}:{source.line_start}-{source.line_end}",
                  f"Commit：{source.commit_sha or '无提交'} · dirty={str(source.dirty).lower()}",
                  f"来源：{source.provenance_kind} · 核验：{source.verification_status} · 运行：{source.execution_status}",
                  f"文件哈希：{source.file_sha256 or source.file_blob_sha} · 片段哈希：{source.excerpt_sha256}",
                  f"相关性：{source.relevance.status} — {esc(source.relevance.reason)}", ""]
        if source.permalink:
            lines += [f"[固定版本来源]({source.permalink})", ""]
        lines += [f"许可观察：{source.license_observation.status}", ""]
        for license in source.license_observation.files:
            lines += [f"许可文件：{esc(license.path)} · {esc(license.identifier or '未识别')} · "
                      f"{license.content_sha256}"]
            if license.permalink:
                lines += [f"[固定版本许可]({license.permalink})"]
        lines += [esc(item) for item in source.license_observation.limitations]
        if source.code_excerpt and source.license_observation.code_display_allowed:
            fence = "`" * max(3, max((len(x) + 1 for x in re.findall(r"`+", source.code_excerpt)), default=3))
            language = source.language if re.fullmatch(r"[A-Za-z0-9_+-]{1,30}", source.language) else "text"
            lines += ["", fence + language, source.code_excerpt, fence, ""]
    lines += ["## 限制", ""] + [esc(item) for item in note.explanation_snapshot.limitations]
    return "\n".join(lines).rstrip() + "\n", "text/markdown"
