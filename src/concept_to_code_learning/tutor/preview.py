"""Ephemeral prose preview. No citations, metadata or savable answers come from it."""

import json
import re


def partial_string(value):
    # An unfinished escape can be completed by later tokens. Keep the last safe
    # prefix without attempting to repair the final model response.
    for trim in range(min(7, len(value))):
        prefix = value[:len(value) - trim] if trim else value
        try:
            return json.loads('"' + prefix + '"').encode("utf-8", errors="ignore").decode("utf-8")
        except ValueError:
            continue
    return ""


def plain_preview(raw, code):
    """Read only top-level prose fields, never keys nested in source metadata."""
    tail, result, decoder = raw.lstrip(), [], json.JSONDecoder()
    if not tail.startswith("{"):
        return []
    tail = tail[1:]
    for _ in range(16):
        tail = tail.lstrip(" \n\r\t,")
        try:
            key, length = decoder.raw_decode(tail)
        except ValueError:
            break
        tail = tail[length:].lstrip()
        if not isinstance(key, str) or not tail.startswith(":"):
            break
        tail = tail[1:].lstrip()
        if key in {"answer", "connection"}:
            match = re.match(r'^"((?:[^"\\]|\\.)*)', tail)
            if match and (text := partial_string(match[1])):
                title = "对应原文" if key == "connection" else "代码怎么实现" if code else "核心意思"
                result.append({"title": title, "text": text})
        try:
            _, length = decoder.raw_decode(tail)
        except ValueError:
            break
        tail = tail[length:]
    return result


def preview_sections(raw, *, code=False):
    raw = raw.lstrip()
    if raw.startswith("```json"):
        raw = raw[7:].lstrip()
    start = re.search(r'"answer_sections"\s*:\s*\[', raw)
    if not start:
        return plain_preview(raw, code)
    tail, result = raw[start.end():], []
    decoder = json.JSONDecoder()
    while tail.strip() and len(result) < 8:
        tail = tail.lstrip(" \n\r\t,")
        if not tail.startswith("{"):
            break
        try:
            value, length = decoder.raw_decode(tail)
        except ValueError:
            value = {}
            for key in ("title", "text"):
                match = re.search(r'(?<!\\)"' + key + r'"\s*:\s*"((?:[^"\\]|\\.)*)', tail)
                if match:
                    value[key] = partial_string(match[1])
            if isinstance(value.get("text"), str) and value["text"]:
                result.append({"title": value.get("title", ""), "text": value["text"]})
            break
        if isinstance(value, dict) and isinstance(value.get("text"), str):
            result.append({"title": value.get("title", "") if isinstance(value.get("title"), str) else "",
                           "text": value["text"]})
        tail = tail[length:]
    return result
