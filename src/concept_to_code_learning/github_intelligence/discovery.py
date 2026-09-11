"""Concept-to-file discovery: bounded text reads and static symbols, never execution."""

import ast
import math
import re
from collections import Counter
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


def tokens(value):
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return {word[:-1] if len(word) > 4 and word.endswith("s") else word
            for word in re.findall(r"[a-z0-9]+", value.casefold())}


def matched(text, terms):
    words, value = tokens(text), text.casefold()
    # A graph clone is not a weighted-graph or priority-queue implementation.
    # Match complete concepts/API tokens instead of any common word fragment.
    return [term for term in terms if (tokens(term) and tokens(term) <= words)
            or (not tokens(term) and term.casefold() in value)]


def ranked_paths(paths, terms, language=None):
    eligible = [
        p
        for p in paths
        if PurePosixPath(p).suffix.lower() in EXTENSIONS
        and not (set(PurePosixPath(p).parts) & IGNORED)
        and not PurePosixPath(p).name.startswith(".")
        and (not language or EXTENSIONS[PurePosixPath(p).suffix.lower()] == language.lower())
    ]
    path_words = {path: tokens(path) for path in eligible}
    frequency = Counter(word for words in path_words.values() for word in words)
    groups = [tokens(term) for term in terms]
    query_words = set().union(*groups) if groups else set()
    weights = {word: math.log(1 + len(eligible) / (1 + frequency[word])) for word in query_words}

    def score(path):
        # Rare names such as an algorithm/API outrank words shared by the whole
        # repository. Filename matches outweigh generic directory names.
        stem = tokens(PurePosixPath(path).stem)
        total = 0
        for index, group in enumerate(groups):
            present = group & path_words[path]
            whole_concept = 1 if present == group else 0.15
            total += whole_concept / (index + 1) ** 2 * sum(
                weights[word] * (3 if word in stem else 1) for word in present)
        return total

    return sorted(
        eligible,
        key=lambda p: (
            PurePosixPath(p).stem in {"__init__", "errors", "exceptions", "version", "_version"},
            any(x in p.lower().split("/") for x in ("tests", "test", "__test__")),
            -score(p),
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
            candidates.append((len(matched(name.rsplit(".", 1)[-1], terms)) * 4 + len(hits),
                               -(end - start), name))
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
