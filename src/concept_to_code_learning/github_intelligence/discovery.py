"""Concept-to-file discovery: bounded text reads and static symbols, never execution."""

import ast
import re
from pathlib import PurePosixPath

from concept_to_code_learning.full_contracts import models as m

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".swift": "swift",
}
IGNORED = {"node_modules", ".git", ".venv", "venv", "vendor", "dist", "build", "__pycache__"}


def matched(text, terms):
    value = text.casefold()
    return [
        term
        for term in terms
        if term.casefold() in value
        or any(len(word) > 3 and word in value for word in re.findall(r"\w+", term.casefold()))
    ]


def ranked_paths(paths, terms, language=None):
    eligible = [
        p
        for p in paths
        if PurePosixPath(p).suffix.lower() in EXTENSIONS
        and not (set(PurePosixPath(p).parts) & IGNORED)
        and not PurePosixPath(p).name.startswith(".")
        and (not language or EXTENSIONS[PurePosixPath(p).suffix.lower()] == language.lower())
    ]
    return sorted(
        eligible,
        key=lambda p: (
            -len(matched(p, terms)),
            PurePosixPath(p).stem in {"__init__", "errors", "exceptions", "version", "_version"},
            any(x in p.lower().split("/") for x in ("tests", "test", "examples")),
            len(p),
            p,
        ),
    )


def python_symbols(text):
    result = []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return result

    def visit(nodes, prefix=""):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                start = min([node.lineno] + [x.lineno for x in node.decorator_list])
                result.append(
                    (
                        name,
                        "class" if isinstance(node, ast.ClassDef) else "function",
                        start,
                        node.end_lineno,
                    )
                )
                visit(node.body, name + ".")

    visit(tree.body)
    return result


def select_symbol(text, path, terms):
    if PurePosixPath(path).suffix.lower() != ".py":
        return None
    candidates = []
    lines = text.splitlines()
    for name, _, start, end in python_symbols(text):
        excerpt = "\n".join(lines[start - 1 : end])
        hits = matched(name + " " + excerpt, terms)
        if hits and len(excerpt) <= 12000 and end - start < 180:
            candidates.append((len(matched(name, terms)) * 4 + len(hits), -(end - start), name))
    return max(candidates)[2] if candidates else None


def candidate(query, repo, handle, ref, path, text):
    if not text.strip():
        return None
    if PurePosixPath(path).suffix == ".py":
        try:
            body = ast.parse(text).body
            if not any(not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                            and isinstance(node.value.value, str)) for node in body):
                return None
        except (SyntaxError, ValueError, RecursionError):
            pass  # A newer language version can still be shown as static text.
    hits = matched(path + "\n" + text, query.concept_terms)
    if not hits:
        return None
    return m.SearchCandidate(
        mode="LIVE",
        candidate_id=m.uid(),
        query_id=query.query_id,
        source_mode=query.source_mode,
        repository=repo,
        local_handle=handle,
        ref_hint=ref,
        file_hint=path,
        symbol_hint=select_symbol(text, path, query.concept_terms),
        matched_terms=hits,
        ranking_reason="概念词出现在路径、符号或源码文本中；语义对应仍需结合讲解判断。",
        discovery_method="bounded_tree_and_static_text",
        discovery_status="CANDIDATE",
        retrieved_at=m.utcnow(),
    )


def result(query, candidates, warnings=()):
    return m.SearchResult(
        mode="LIVE",
        query_id=query.query_id,
        candidates=candidates,
        selection_required=False,
        status="CANDIDATES" if candidates else "NO_RELEVANT_SOURCE",
        warnings=list(warnings),
    )
