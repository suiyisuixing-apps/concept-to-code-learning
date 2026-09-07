"""A deterministic dependency-injection lesson; no model, search, or runtime execution."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from concept_to_code_learning.contracts import load_schemas, validate_record

QUESTION = "依赖注入到底是什么？真实项目中怎么使用？"
LEVELS = ("Beginner", "University", "Engineering", "Source-code level")
TEXT = {
    "Beginner": "依赖注入可以理解为：函数先列出需要的材料，外部把材料送进来。"
    "在这里，read_items 需要 commons，FastAPI 根据 Depends(common_parameters) "
    "取得它，再交给函数。函数使用收到的值，不需要自己重复处理查询参数。",
    "University": "依赖注入将依赖的声明与提供分开。read_items 的参数通过 "
    "Annotated 和 Depends 声明 common_parameters，框架解析请求参数、调用依赖，"
    "并把返回值绑定到 commons。这体现了控制反转，也让参数处理逻辑可以复用。",
    "Engineering": "把多个接口共享的查询参数处理集中到 common_parameters，"
    "通过 Depends 注入到 read_items。业务入口只消费 commons。工程实现还需要"
    "验证异常、生命周期和测试覆盖；此片段只展示参数依赖，不能证明认证或数据库安全。",
    "Source-code level": "第 12 行注册 /items/ 路由；第 13 行的 "
    "Annotated[dict, Depends(common_parameters)] 同时表达参数类型与依赖元数据；"
    "第 14 行返回注入的 commons。框架如何构建和解析依赖图需要进一步核验其他源码，"
    "当前三行片段不足以回答该内部机制。",
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FixtureTutor:
    def __init__(self, root: Path):
        self.schemas = load_schemas(root)
        folder = root / "demo/learning"
        self.document = json.loads((folder / "document.json").read_text())
        self.source = json.loads((folder / "github-source.json").read_text())
        validate_record("github-code-source", self.source, self.schemas)
        if digest(self.source["code_excerpt"]) != self.source["excerpt_hash"]:
            raise ValueError("NEEDS_CONFIRMATION: frozen source excerpt hash mismatch")

    def context(self, page: int = 1, selected: str = "") -> dict:
        item = self.document["pages"][page - 1]
        return {
            "document_id": self.document["document_id"],
            "file_name": self.document["file_name"], "source_type": "MARKDOWN_FIXTURE",
            "current_page": page, "current_slide": None, "current_section": item["section"],
            "selected_text": selected, "selected_text_hash": digest(selected) if selected else None,
        }

    def session(self) -> dict:
        return {
            "mode": "FIXTURE", "status": "SCAFFOLD_DEMO", "document": self.document,
            "question": QUESTION, "explanation_levels": list(LEVELS),
            "document_context": self.context(),
            "capabilities": {"notes_persisted": True, "live_search": False,
                             "general_verification": False, "document_import": False,
                             "local_model": False},
        }

    def explain(self, question: str, context: dict, level: str) -> dict:
        validate_record("document-context", context, self.schemas)
        page = context["current_page"]
        if not isinstance(page, int) or not 1 <= page <= len(self.document["pages"]):
            raise ValueError("NEEDS_CONFIRMATION: page is outside the synthetic document")
        selected = context["selected_text"]
        if context != self.context(page, selected):
            raise ValueError("NEEDS_CONFIRMATION: context or selection hash does not match")
        page_text = "\n\n".join(self.document["pages"][page - 1]["paragraphs"])
        if selected and selected not in page_text:
            raise ValueError("NEEDS_CONFIRMATION: selection is not present on this page")
        if level not in LEVELS:
            raise ValueError("NEEDS_CONFIRMATION: unsupported explanation level")
        if not any(term in question.lower() for term in
                   ("依赖", "注入", "dependency", "fastapi", "depends", "commons")):
            raise ValueError("NEEDS_CONFIRMATION: Fixture 仅支持依赖注入主题，请使用示例问题。")
        quote = selected or page_text
        citation = {
            "document_id": context["document_id"], "file_name": context["file_name"],
            "source_type": context["source_type"], "page": page, "slide": None,
            "section": context["current_section"], "quote": quote, "quote_hash": digest(quote),
        }
        response = {
            "grounded_explanation_id": str(uuid4()), "mode": "FIXTURE",
            "status": "SCAFFOLD_DEMO", "question": question, "document_context": context,
            "concept": {
                "concept_id": "dependency-injection", "name": "依赖注入",
                "description": "外部提供函数所需的依赖。", "keywords": ["FastAPI", "Depends"],
                "document_context": context, "status": "NEEDS_CONFIRMATION",
            },
            "explanation_level": level,
            "explanation": f"{TEXT[level]}\n\n当前依据：第 {page} 页「{context['current_section']}」。"
            + (f"你选中了「{selected}」。" if selected else "本次使用当前页全文。"),
            "document_citations": [citation], "github_sources": [deepcopy(self.source)],
            "code_comparison": [], "runnable_example_status": "NOT_RUN",
            "unresolved_items": [
                "这是人工编写的固定讲解，未调用 AI 模型。",
                "仅核验一条冻结的官方代码来源，运行时没有实时搜索或通用核验。",
                "未运行该 GitHub 片段；多仓库比较与真正文档导入待实现。",
            ],
        }
        validate_record("grounded-explanation", response, self.schemas)
        return response
