"""Explicit context-only bridge. It cannot upgrade client source receipts or old notes."""

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.context import resolve_context
from concept_to_code_learning.full_learning.errors import require


def from_sprint_context(value: dict) -> m.DocumentContext:
    require(value.get("contract_version") == "sprint-1" and value["source_type"] in {
        "PPTX", "MARKDOWN_FIXTURE"}, "INCOMPATIBLE_CONTRACT", "compat", "只接受原 Sprint 1 文档合同。")
    pptx = value["source_type"] == "PPTX"
    index = value["current_slide"] if pptx else value["current_page"]
    locator = m.SourceLocator(unit_type="slide" if pptx else "section", index=index,
                              heading_path=[value["current_section"]] if value["current_section"] else [])
    block_id = "legacy-" + m.digest(value["visible_text"])[:24]
    unit_id = "legacy-unit-" + str(index)
    record = m.DocumentRecord(mode=value["mode"], document_id=value["document_id"],
        file_name=value["file_name"], source_type="PPTX" if pptx else "MARKDOWN",
        original_sha256=value["file_hash"], unit_count=index, import_status="READY",
        created_at=m.utcnow(), warnings=["LEGACY_CONTEXT_BRIDGE: 原始聚合文本，不代表重新解析了文档。"])
    block = m.Block(block_id=block_id, kind="paragraph", text=value["visible_text"], source_locator=locator)
    unit = m.DocumentUnit(mode=value["mode"], document_id=record.document_id, document_revision=1,
        unit_id=unit_id, unit_type=locator.unit_type, index=index, blocks=[block], source_locator=locator,
        preview=m.Preview(kind="learning_view", fidelity="extracted"), extraction_status="READY")
    selection = None
    if value["selected_text"]:
        require(value["visible_text"].count(value["selected_text"]) == 1,
                "SELECTION_MISMATCH", "compat", "旧选区不能唯一定位到字符范围。")
        start = value["visible_text"].index(value["selected_text"])
        selection = m.SelectionLocator(spans=[m.SelectionSpan(block_id=block_id, start=start,
            end=start + len(value["selected_text"]))])
    return resolve_context(record, unit, m.ContextRequest(document_revision=1, unit_id=unit_id,
        selected_text=value["selected_text"], selected_text_hash=value["selected_text_hash"],
        selection_locator=selection))


def to_sprint_context(context: m.DocumentContext) -> dict:
    require(bool(context.visible_text.strip()) and (
        context.source_type == "PPTX" and context.mode == "LIVE" or
        context.source_type == "MARKDOWN" and context.mode == "FIXTURE"),
        "INCOMPATIBLE_CONTRACT", "compat", "该格式或空白页无法无损投影到旧 PPTX/Fixture 合同。")
    pptx = context.source_type == "PPTX"
    return {"contract_version": "sprint-1", "document_id": context.document_id,
            "file_name": context.file_name, "source_type": "PPTX" if pptx else "MARKDOWN_FIXTURE",
            "file_hash": context.original_sha256, "current_page": None if pptx else context.unit_locator.index,
            "current_slide": context.unit_locator.index if pptx else None,
            "current_section": None if pptx else "/".join(context.unit_locator.heading_path) or "Legacy fixture",
            "visible_text": context.visible_text, "selected_text": context.selected_text,
            "selected_text_hash": context.selected_text_hash, "mode": context.mode}
