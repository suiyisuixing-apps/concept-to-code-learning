"""Resolve selected text from server-owned blocks, using end-exclusive offsets."""

from concept_to_code_learning.full_contracts.models import (
    ContextRequest,
    DocumentContext,
    DocumentRecord,
    DocumentUnit,
    digest,
)
from concept_to_code_learning.full_learning.errors import require


def resolve_context(record: DocumentRecord, unit: DocumentUnit,
                    request: ContextRequest) -> DocumentContext:
    require(record.revision == request.document_revision
            and unit.document_revision == request.document_revision,
            "DOCUMENT_VERSION_MISMATCH", "document", "文档版本已变化，请重新选择当前位置。", 409)
    expected_type = {"PDF": "page", "PPTX": "slide", "DOCX": "section", "MARKDOWN": "section", "CODE": "section"}
    require(unit.document_id == record.document_id and unit.unit_id == request.unit_id
            and unit.unit_type == expected_type[record.source_type]
            and unit.index <= record.unit_count and unit.mode == record.mode,
            "DOCUMENT_VERSION_MISMATCH", "document", "文档单元与服务端记录不匹配。", 409)
    blocks = {block.block_id: block for block in unit.blocks}
    selected = ""
    if request.selection_locator:
        parts, positions = [], []
        order = {block.block_id: index for index, block in enumerate(unit.blocks)}
        for span in request.selection_locator.spans:
            require(span.block_id in blocks, "SELECTION_MISMATCH", "document", "选区块不存在。")
            block = blocks[span.block_id]
            require(span.end <= len(block.text), "SELECTION_MISMATCH", "document",
                    "选区超出服务端文本范围。")
            position = (order[span.block_id], span.start, span.end)
            require(not positions or position[0] > positions[-1][0]
                    or position[0] == positions[-1][0] and position[1] >= positions[-1][2],
                    "SELECTION_MISMATCH", "document", "选区重复、重叠或顺序不明确。")
            positions.append(position)
            parts.append(block.text[span.start:span.end])
        selected = "\n".join(parts)
        normalize = (lambda text: " ".join(text.split())) if (
            request.selection_locator.normalization == "whitespace-v1") else (lambda text: text)
        require(normalize(selected) == normalize(request.selected_text), "SELECTION_MISMATCH",
                "document", "提交的选中文字与服务端保存的文本不一致。")
        # Preserve the actual stored text; the normalization rule is retained in the locator.
    else:
        require(not request.selected_text and request.selected_text_hash is None,
                "SELECTION_MISMATCH", "document", "选中文字必须携带块 ID 和字符范围。")
    require(request.selected_text_hash is None or request.selected_text_hash == digest(selected),
            "SELECTION_MISMATCH", "document", "选区内容哈希不匹配。")
    visible = "\n".join(block.text for block in unit.blocks if block.text)
    empty = not visible.strip()
    return DocumentContext(
        mode=record.mode, document_id=record.document_id, document_revision=record.revision,
        original_sha256=record.original_sha256, source_type=record.source_type,
        file_name=record.file_name, unit_id=unit.unit_id, unit_locator=unit.source_locator,
        visible_text=visible, selected_text=selected,
        selected_text_hash=digest(selected) if selected else None,
        selection_locator=request.selection_locator,
        relevant_context_blocks=unit.blocks + unit.supporting_blocks,
        code_location=record.code_location, code_license=record.code_license,
        coverage="NO_EXTRACTABLE_TEXT" if empty else (
            "TEXT" if unit.extraction_status == "READY" else "PARTIAL"),
        warnings=record.warnings + unit.warnings,
        status="NO_EXTRACTABLE_TEXT" if empty else (
            "READY" if unit.extraction_status == "READY" else "PARTIAL"))
