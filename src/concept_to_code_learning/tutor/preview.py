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


def preview_sections(raw):
    start = re.search(r'"answer_sections"\s*:\s*\[', raw)
    if not start:
        return []
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
