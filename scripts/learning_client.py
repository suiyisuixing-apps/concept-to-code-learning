"""Portable, standard-library Skill client for the local full-delivery-v1 API."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

PREFIX = "/api/learning/v1"


class ClientError(Exception):
    def __init__(self, code, message, status=None):
        self.payload = {"code": code, "user_message": message, "http_status": status}
        super().__init__(code)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ClientError("REDIRECT_NOT_ALLOWED", "本地 API 不允许重定向到其他地址。", code)


class Client:
    def __init__(self, base_url="http://127.0.0.1:8766"):
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.path not in {"", "/"} or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise ClientError("ENDPOINT_NOT_AUTHORIZED", "Skill 客户端只连接明确的本机服务。")
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method, path, body=None, *, raw=None, as_text=False):
        if not path.startswith(PREFIX + "/"):
            raise ClientError("PATH_NOT_AUTHORIZED", "仅允许完整学习版 API。")
        data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode("utf-8")
                                            if body is not None else None)
        content_type = "application/octet-stream" if raw is not None else "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, method=method,
                                         headers={"Content-Type": content_type, "Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=150) as response:
                content = response.read(16 * 1024 * 1024 + 1)
                if len(content) > 16 * 1024 * 1024:
                    raise ClientError("RESPONSE_TOO_LARGE", "响应过大，请分页读取。")
                text = content.decode("utf-8")
                return text if as_text else (json.loads(text) if text else {"status": "DONE"})
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read(32768).decode("utf-8"))
            except (ValueError, UnicodeError):
                payload = {}
            raise ClientError(payload.get("code", "HTTP_ERROR"),
                              payload.get("user_message", "本地服务拒绝了请求。"), exc.code) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ClientError("SERVICE_UNAVAILABLE", "本地服务未连接或超时，请启动软件后重试。") from exc


def scope(args):
    return {"source_mode": args.source_mode, "repository_allowlist": args.repo,
            "network_authorized": args.network_authorized, "local_handle": args.local_handle,
            "query_terms_approved": bool(args.approved_term), "approved_query_terms": args.approved_term}


def learn(client, args):
    path = Path(args.file)
    if not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:
        raise ClientError("INVALID_FILE", "请提供不超过 20 MiB 的已授权文件。")
    document = client.request("POST", PREFIX + "/documents?" + urllib.parse.urlencode({"file_name": path.name}),
                              raw=path.read_bytes())
    units = client.request("GET", f'{PREFIX}/documents/{document["document_id"]}/units')["units"]
    unit = next((item for item in units if item["index"] == args.unit_index), None)
    if unit is None:
        raise ClientError("INVALID_UNIT", "所选页、Slide 或章节不存在。")
    selection = None
    if args.selected_text:
        matches = []
        for block in unit["blocks"]:
            start = 0
            while (position := block["text"].find(args.selected_text, start)) >= 0:
                matches.append({"block_id": block["block_id"], "start": position,
                                "end": position + len(args.selected_text)})
                start = position + 1
        if len(matches) != 1:
            raise ClientError("SELECTION_MISMATCH", "选区不能唯一定位；请在阅读器中选择准确范围。")
        selection = {"spans": matches, "normalization": "exact"}
    session = client.request("POST", PREFIX + "/sessions")
    session = client.request("POST", f'{PREFIX}/sessions/{session["session_id"]}/context', {
        "document_id": document["document_id"], "document_revision": document["revision"],
        "unit_id": unit["unit_id"], "expected_context_revision": session["context_revision"],
        "selected_text": args.selected_text, "selection_locator": selection})
    return client.request("POST", PREFIX + "/explanations", {
        "request_id": str(uuid4()), "session_id": session["session_id"],
        "context_revision": session["context_revision"], "question": args.question,
        "level": args.level, "scope": scope(args), "compare": args.compare})


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    learning = sub.add_parser("learn")
    learning.add_argument("--file", required=True)
    learning.add_argument("--question", required=True)
    learning.add_argument("--unit-index", type=int, default=1)
    learning.add_argument("--selected-text", default="")
    learning.add_argument("--level", choices=["Beginner", "University", "Engineering", "Source-code"], default="Beginner")
    learning.add_argument("--source-mode", choices=["specified_public", "public_search", "local_authorized"], default="specified_public")
    learning.add_argument("--repo", action="append", default=[])
    learning.add_argument("--local-handle")
    learning.add_argument("--network-authorized", action="store_true")
    learning.add_argument("--approved-term", action="append", default=[])
    learning.add_argument("--compare", action="store_true")
    request = sub.add_parser("explain", help="追问/候选选择：读取符合 ExplanationRequest 的本地 JSON。")
    request.add_argument("--request-json", required=True)
    notes = sub.add_parser("notes")
    notes.add_argument("--query", default="")
    notes.add_argument("--offset", type=int, default=0)
    save = sub.add_parser("save")
    save.add_argument("--session-id", required=True)
    save.add_argument("--explanation-id", required=True)
    save.add_argument("--idempotency-key", required=True)
    save.add_argument("--title", required=True)
    save.add_argument("--text", default="")
    save.add_argument("--confirm", action="store_true")
    edit = sub.add_parser("edit-note")
    edit.add_argument("--note-id", required=True)
    edit.add_argument("--revision", required=True, type=int)
    edit.add_argument("--title", required=True)
    edit.add_argument("--text", default="")
    delete = sub.add_parser("delete-note")
    delete.add_argument("--note-id", required=True)
    delete.add_argument("--revision", required=True, type=int)
    delete.add_argument("--confirm", action="store_true")
    export = sub.add_parser("export-note")
    export.add_argument("--note-id", required=True)
    export.add_argument("--format", choices=["markdown", "json"], default="markdown")
    cancel = sub.add_parser("cancel")
    cancel.add_argument("--session-id", required=True)
    cancel.add_argument("--request-id", required=True)
    args = parser.parse_args(argv)
    try:
        client = Client(args.base_url)
        if args.command == "capabilities":
            result = client.request("GET", PREFIX + "/capabilities")
        elif args.command == "learn":
            result = learn(client, args)
        elif args.command == "explain":
            body = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
            result = client.request("POST", PREFIX + "/explanations", body)
        elif args.command == "notes":
            result = client.request("GET", PREFIX + "/notes?" + urllib.parse.urlencode({
                "q": args.query, "offset": args.offset, "limit": 20}))
        elif args.command == "save":
            if not args.confirm:
                raise ClientError("EXPLICIT_SAVE_REQUIRED", "只有用户明确要求保存后才能使用 --confirm。")
            result = client.request("POST", PREFIX + "/notes", {"session_id": args.session_id,
                "explanation_id": args.explanation_id, "idempotency_key": args.idempotency_key,
                "save_requested_by_user": True, "title": args.title, "user_text": args.text})
        elif args.command == "edit-note":
            result = client.request("PATCH", f"{PREFIX}/notes/{urllib.parse.quote(args.note_id, safe='')}", {
                "expected_revision": args.revision, "title": args.title, "user_text": args.text})
        elif args.command == "delete-note":
            if not args.confirm:
                raise ClientError("DELETE_CONFIRMATION_REQUIRED", "删除笔记需要用户明确确认。")
            result = client.request("DELETE", f"{PREFIX}/notes/{urllib.parse.quote(args.note_id, safe='')}", {
                "expected_revision": args.revision, "confirmed_by_user": True})
        elif args.command == "export-note":
            result = client.request("GET", f"{PREFIX}/notes/{urllib.parse.quote(args.note_id, safe='')}/export?"
                                    + urllib.parse.urlencode({"format": args.format}), as_text=True)
        else:
            result = client.request("DELETE", f"{PREFIX}/requests/{urllib.parse.quote(args.request_id, safe='')}?"
                                    + urllib.parse.urlencode({"session_id": args.session_id}))
        print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ClientError as exc:
        print(json.dumps(exc.payload, ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({"code": "INVALID_INPUT", "user_message": "无法读取输入文件或解析响应。"},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
