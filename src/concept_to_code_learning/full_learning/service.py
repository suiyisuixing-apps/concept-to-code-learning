"""Server-owned context, bounded retrieval, verified evidence and grounded teaching."""

import asyncio
import re
from copy import deepcopy

from pydantic import ValidationError

from concept_to_code_learning.full_contracts import models as m
from concept_to_code_learning.full_learning.context import resolve_context
from concept_to_code_learning.full_learning.errors import LearningError, require
from concept_to_code_learning.full_learning.ports import ProviderBundle, VerificationReceipt
from concept_to_code_learning.full_learning.store import LearningStore, canonical


class LearningService:
    def __init__(self, providers: ProviderBundle, store: LearningStore, *, timeout_seconds: float = 60):
        self.providers, self.store = providers, store
        self.timeout_seconds = timeout_seconds
        self.active: dict[str, asyncio.Task] = {}

    async def call(self, stage, action, *args, **kwargs):
        try:
            async with asyncio.timeout(self.timeout_seconds):
                return await action(*args, **kwargs)
        except LearningError:
            raise
        except TimeoutError as exc:
            raise LearningError("MODEL_UNAVAILABLE" if stage == "tutor" else "PROVIDER_TIMEOUT",
                                stage, "模块响应超时，未切换到其他数据来源或模型。", 504,
                                retryable=True) from exc
        except ValidationError as exc:
            raise LearningError("MODEL_OUTPUT_INVALID" if stage == "tutor" else "SOURCE_MISMATCH",
                                stage, "模块返回的数据不符合公共合同。", 502) from exc
        except Exception as exc:
            raise LearningError("MODEL_UNAVAILABLE" if stage == "tutor" else "PROVIDER_UNAVAILABLE",
                                stage, "模块调用失败；未使用替身或云端作为回退。", 503,
                                retryable=True) from exc

    async def provider_capability(self, provider, stage: str) -> m.ProviderCapability:
        try:
            async with asyncio.timeout(min(self.timeout_seconds, 3)):
                value = await provider.capabilities()
                capability = m.ProviderCapability.model_validate(value)
                require(not capability.available or capability.implemented,
                        "INVALID_CAPABILITY", stage, "模块能力声明不一致。", 503)
                require(not capability.available or capability.mode != "UNAVAILABLE",
                        "INVALID_CAPABILITY", stage, "模块尚不可用。", 503)
                return capability
        except (Exception, TimeoutError):
            return m.ProviderCapability(provider_id=stage, implemented=False, available=False,
                                        mode="UNAVAILABLE", features=[], status="UNAVAILABLE",
                                        reason_code="HEALTH_CHECK_FAILED",
                                        needed_action="检查已安装模块及其配置。")

    async def capabilities(self) -> m.Capabilities:
        doc, sources, tutor = await asyncio.gather(
            self.provider_capability(self.providers.document, "document"),
            self.provider_capability(self.providers.sources, "sources"),
            self.provider_capability(self.providers.tutor, "tutor"))
        ready = all(x.available for x in (doc, sources, tutor))
        fixture = any(x.mode == "FIXTURE" for x in (doc, sources, tutor))
        return m.Capabilities(mode="UNAVAILABLE" if not ready else ("FIXTURE" if fixture else "LIVE"),
                              document=doc, sources=sources, tutor=tutor,
                              integrated_product="UNAVAILABLE" if not ready else (
                                  "FIXTURE" if fixture else "READY_FOR_LIVE_CHECK"),
                              status="PARTIAL" if not ready else ("FIXTURE" if fixture else "AVAILABLE"))

    async def context(self, document_id: str, request: m.ContextRequest) -> m.DocumentContext:
        record = m.DocumentRecord.model_validate(await self.call(
            "document", self.providers.document.get_document, document_id))
        unit = m.DocumentUnit.model_validate(await self.call(
            "document", self.providers.document.get_unit, document_id, request.unit_id))
        require(record.document_id == document_id, "DOCUMENT_VERSION_MISMATCH", "document",
                "返回了不同文档。", 409)
        return resolve_context(record, unit, request)

    async def activate(self, session_id: str, request: m.ActivateContext) -> m.SessionRecord:
        self.store.session(session_id)
        context = await self.context(request.document_id, m.ContextRequest.model_validate(
            request.model_dump(exclude={"document_id", "expected_context_revision"})))
        result = self.store.activate(session_id, context, request.expected_context_revision)
        # The transaction invalidates earlier epochs before workers are interrupted.
        for request_id, task in list(self.active.items()):
            try:
                self.store.check_request(request_id)
            except LearningError:
                task.cancel()
        return result

    async def cancel(self, session_id: str, request_id: str):
        self.store.cancel(session_id, request_id)
        task = self.active.get(request_id)
        if task:
            task.cancel()

    @staticmethod
    def make_query(scope: m.SourceScope, terms: list[str], mode: m.Mode) -> m.SourceQuery:
        terms = list(dict.fromkeys(term.strip() for term in terms if term.strip()))
        require(bool(terms), "NO_RELEVANT_SOURCE", "sources", "没有可用于检索的概念词。")
        if scope.source_mode == "local_authorized":
            require(bool(scope.local_handle), "AUTH_REQUIRED", "sources", "请选择已授权的本地仓库句柄。")
        else:
            if not scope.network_authorized:
                raise LearningError("NETWORK_NOT_AUTHORIZED", "sources", "当前未授权 GitHub 联网。",
                                    needed_action="明确选择仓库或公开搜索，并确认联网范围。")
            if scope.source_mode == "specified_public":
                require(bool(scope.repository_allowlist), "NO_RELEVANT_SOURCE", "sources",
                        "未选择公开仓库；可先阅读文档讲解。")
            else:
                allowed = {term.casefold() for term in scope.approved_query_terms}
                if not scope.query_terms_approved or not all(term.casefold() in allowed for term in terms):
                    raise LearningError("QUERY_TERMS_NOT_APPROVED", "sources",
                                        "公开搜索词尚未逐项得到授权；未发送课件或问题原文。",
                                        needed_action="确认本次必要概念词 approved_query_terms 后重试。")
        # Source clients receive only necessary concept terms, never the full document/question.
        return m.SourceQuery(**scope.model_dump(), mode=mode, query_id=m.uid(),
                             question=" ".join(terms), concept_terms=terms, status="AUTHORIZED")

    @staticmethod
    def scope_hash(scope: m.SourceScope) -> str:
        return m.digest(canonical(scope))

    async def search(self, request: m.SearchRequest) -> m.SearchResult:
        session = self.store.session(request.session_id)
        require(session.context_revision == request.context_revision and session.context is not None,
                "CANCELLED", "context", "检索上下文已变化。", 409)
        capability = await self.provider_capability(self.providers.sources, "sources")
        query = self.make_query(request.scope, request.concept_terms, capability.mode)
        if query.source_mode == "local_authorized":
            handles = await self.call("sources", self.providers.sources.local_handles)
            require(query.local_handle in handles, "AUTH_REQUIRED", "sources", "本地仓库句柄尚未授权。")
        result = m.SearchResult.model_validate(await self.call("sources", self.providers.sources.search, query))
        require(result.query_id == query.query_id and result.mode == capability.mode,
                "SOURCE_MISMATCH", "sources", "检索返回了不同请求或模式。", 502)
        require(len(result.candidates) <= query.scope_limit.files
                and len({c.candidate_id for c in result.candidates}) == len(result.candidates),
                "SOURCE_MISMATCH", "sources", "候选数量或标识不符合范围限制。", 502)
        repos = set()
        for candidate in result.candidates:
            require(candidate.query_id == query.query_id and candidate.source_mode == query.source_mode
                    and candidate.mode == query.mode, "SOURCE_MISMATCH", "sources", "候选检索绑定不一致。", 502)
            if query.source_mode == "local_authorized":
                require(candidate.local_handle == query.local_handle and candidate.repository is None,
                        "SOURCE_MISMATCH", "sources", "候选超出授权本地仓库。", 502)
            else:
                require(candidate.repository is not None, "SOURCE_MISMATCH", "sources", "候选缺少仓库标识。", 502)
                repos.add(candidate.repository)
                if query.source_mode == "specified_public":
                    require(candidate.repository in query.repository_allowlist, "SOURCE_MISMATCH",
                            "sources", "候选超出指定仓库范围。", 502)
        require(len(repos) <= query.scope_limit.repositories, "SOURCE_MISMATCH", "sources",
                "候选仓库数量超出本次限制。", 502)
        self.store.put_query(request.session_id, request.context_revision, query,
                             self.scope_hash(request.scope), result)
        return result

    async def verify(self, request: m.VerifyRequest) -> m.CodeEvidence:
        query, result, scope_hash = self.store.query(request.session_id, request.query_id)
        candidate = next((c for c in result.candidates if c.candidate_id == request.candidate_id), None)
        require(candidate is not None and candidate.discovery_status != "REJECTED", "SOURCE_MISMATCH",
                "sources", "候选不属于本次服务端检索。", 404)
        if query.source_mode == "local_authorized":
            handles = await self.call("sources", self.providers.sources.local_handles)
            require(query.local_handle in handles, "AUTH_REQUIRED", "sources", "本地仓库授权已失效。", 403)
        receipt = await self.call("sources", self.providers.sources.verify,
                                  query.model_copy(deep=True), candidate.model_copy(deep=True), scope_hash)
        require(isinstance(receipt, VerificationReceipt) and receipt.query_id == query.query_id
                and receipt.candidate_id == candidate.candidate_id and receipt.scope_sha256 == scope_hash,
                "SOURCE_MISMATCH", "sources", "缺少绑定当前检索范围的服务端核验结果。", 502)
        evidence = m.CodeEvidence.model_validate(receipt.evidence)
        require(evidence.mode == query.mode and evidence.source_mode == query.source_mode,
                "SOURCE_MISMATCH", "sources", "来源模式与本次检索不匹配。", 502)
        if query.source_mode == "local_authorized":
            require(evidence.local_handle == query.local_handle, "SOURCE_MISMATCH", "sources",
                    "来源超出本地授权。", 502)
        else:
            require(f"{evidence.repository_owner}/{evidence.repository_name}" == candidate.repository,
                    "SOURCE_MISMATCH", "sources", "核验结果属于不同仓库。", 502)
        require(not candidate.file_hint or evidence.file_path == candidate.file_hint,
                "SOURCE_MISMATCH", "sources", "核验结果属于不同文件。", 502)
        require(not candidate.symbol_hint or evidence.symbol == candidate.symbol_hint,
                "SOURCE_MISMATCH", "sources", "核验符号与候选不同。", 502)
        if candidate.ref_hint:
            require((evidence.commit_sha == candidate.ref_hint if re.fullmatch(r"[a-f0-9]{40}", candidate.ref_hint)
                     else evidence.requested_ref == candidate.ref_hint),
                    "SOURCE_MISMATCH", "sources", "核验结果没有固定所选版本。", 502)
        if evidence.verification_status == "VERIFIED":
            checks = {"file", "line_range", "excerpt_hash", "license", "scope"}
            if evidence.commit_sha:
                checks.add("commit")
            if query.source_mode != "local_authorized":
                checks.add("public_repository")
            require(all(evidence.verification_checks.get(c) == "PASSED" for c in checks),
                    "SOURCE_MISMATCH", "sources", "来源缺少必需的独立核验步骤。", 502)
            expected_ast = "PASSED" if evidence.language.lower() == "python" and evidence.symbol else "NOT_APPLICABLE"
            require(evidence.verification_checks.get("python_symbol") == expected_ast,
                    "SOURCE_MISMATCH", "sources", "静态符号核验状态不正确。", 502)
            require(evidence.provenance_kind == "SOURCE_EXACT" and evidence.execution_status == "NOT_RUN",
                    "SOURCE_MISMATCH", "sources", "本版核验器只能提供未执行的原始来源。", 502)
        for license_file in evidence.license_observation.files:
            require(not license_file.path.startswith(("/", "\\"))
                    and ".." not in license_file.path.split("/"),
                    "SOURCE_MISMATCH", "sources", "许可记录路径不合法。", 502)
            if query.source_mode != "local_authorized":
                from urllib.parse import quote
                prefix = f"{evidence.repository_url}/blob/{evidence.commit_sha}/"
                require(license_file.commit_sha == evidence.commit_sha
                        and license_file.permalink == prefix + quote(license_file.path, safe="/"),
                        "SOURCE_MISMATCH", "sources", "许可记录没有绑定相同固定版本。", 502)
        self.store.put_source(request.session_id, query.query_id, evidence)
        return evidence

    @staticmethod
    def usable(source: m.CodeEvidence) -> bool:
        return (source.verification_status == "VERIFIED" and bool(source.code_excerpt)
                and source.license_observation.code_display_allowed
                and source.relevance.status != "NOT_RELEVANT")

    async def existing_sources(self, session_id: str, source_ids: list[str], scope: m.SourceScope):
        require(len(set(source_ids)) == len(source_ids) and len(source_ids) <= scope.max_sources,
                "SOURCE_MISMATCH", "sources", "来源数量或 ID 重复。")
        sources = []
        if scope.source_mode == "local_authorized":
            handles = await self.call("sources", self.providers.sources.local_handles)
            require(scope.local_handle in handles, "AUTH_REQUIRED", "sources", "本地仓库授权已失效。", 403)
        for source_id in source_ids:
            source, _, scope_hash = self.store.source(session_id, source_id)
            require(scope_hash == self.scope_hash(scope), "SOURCE_MISMATCH", "sources",
                    "来源的原授权范围与当前请求不同，请重新检索。", 409)
            require(self.usable(source), "SOURCE_MISMATCH", "sources", "来源尚不能作为代码证据。")
            sources.append(source)
        return sources

    @staticmethod
    def validate_answer(answer: m.GroundedExplanation, context: m.DocumentContext,
                        sources: list[m.CodeEvidence], plan: m.TeachingPlan, compare: bool,
                        tutor_mode: m.Mode):
        require(answer.context_snapshot == context and answer.question == plan.question
                and answer.level == plan.level, "CITATION_INVALID", "tutor", "讲解改变了冻结上下文或问题。", 502)
        require(not answer.unsupported_claims, "CITATION_INVALID", "tutor",
                "模型报告了无据断言；本次回答未被标记为有据。", 502)
        source_map = {s.source_id: s for s in sources}
        require(len(set(answer.code_source_ids)) == len(answer.code_source_ids)
                and set(answer.code_source_ids) <= source_map.keys(), "CITATION_INVALID", "tutor",
                "模型引用了未核验或重复的来源 ID。", 502)
        blocks = {b.block_id: b for b in context.relevant_context_blocks}
        require(bool(answer.document_citations), "CITATION_INVALID", "tutor", "缺少文档依据。", 502)
        for citation in answer.document_citations:
            require(citation.block_id in blocks and citation.quote in blocks[citation.block_id].text
                    and citation.quote_sha256 == m.digest(citation.quote),
                    "CITATION_INVALID", "tutor", "文档引用不是服务端保存的原文。", 502)
        for link in answer.concept_code_links:
            require(link.source_id in answer.code_source_ids
                    and (link.symbol is None or link.symbol == source_map[link.source_id].symbol),
                    "CITATION_INVALID", "tutor", "概念引用了未核验的代码符号。", 502)
        for example in answer.example_blocks:
            require(example.execution_status == "NOT_RUN", "CITATION_INVALID", "tutor",
                    "本版未执行来源代码，不能宣称已有运行结果。", 502)
            if example.provenance_kind == "AI_GENERATED":
                require(example.source_id is None, "CITATION_INVALID", "tutor", "生成示例不能冒充仓库来源。", 502)
            else:
                require(example.source_id in answer.code_source_ids, "CITATION_INVALID", "tutor",
                        "改编或原始示例缺少已核验来源。", 502)
                if example.provenance_kind == "SOURCE_EXACT":
                    require(example.code == source_map[example.source_id].code_excerpt,
                            "CITATION_INVALID", "tutor", "原始代码被模型改写。", 502)
        if compare or answer.comparison:
            require(answer.comparison is not None and len(set(answer.comparison.source_ids)) >= 2
                    and set(answer.comparison.source_ids) <= set(answer.code_source_ids),
                    "CITATION_INVALID", "tutor", "比较需要至少两条独立核验来源。", 502)
            identities = {(source_map[s].repository_url, source_map[s].local_handle)
                          for s in answer.comparison.source_ids}
            require(len(identities) >= 2, "CITATION_INVALID", "tutor", "本次比较需要两个不同仓库。", 502)
        prose = [text for section in answer.answer_sections for text in (section.title, section.text)]
        prose += answer.limitations + [text for link in answer.concept_code_links
                                       for text in (link.concept, link.reason)]
        prose += [example.explanation for example in answer.example_blocks]
        if answer.metrics.truncation_reason:
            prose.append(answer.metrics.truncation_reason)
        if answer.comparison:
            prose += [answer.comparison.summary, *answer.comparison.tradeoffs]
        require(not any(re.search(r"(?:https?://|www\.)", text, re.I) for text in prose),
                "CITATION_INVALID", "tutor", "模型输出了任意网址；请用来源或文档 ID 引用。", 502)
        live = context.mode == "LIVE" and all(s.mode == "LIVE" for s in sources) and tutor_mode == "LIVE"
        require(answer.mode == ("LIVE" if live else "FIXTURE")
                and answer.provider_info.mode == tutor_mode,
                "MODEL_OUTPUT_INVALID", "tutor", "讲解模式不能覆盖替身依赖的真实状态。", 502)
        if live:
            require(bool(answer.provider_info.model_id) and answer.provider_info.status == "AVAILABLE"
                    and answer.provider_info.endpoint_kind in {"loopback", "authorized_remote"},
                    "MODEL_OUTPUT_INVALID", "tutor", "真实模型调用缺少模型身份。", 502)
            require(answer.status == ("GROUNDED" if answer.code_source_ids else "NO_VERIFIED_CODE"),
                    "MODEL_OUTPUT_INVALID", "tutor", "回答状态与代码覆盖不一致。", 502)
        else:
            require(answer.status == "FIXTURE", "MODEL_OUTPUT_INVALID", "tutor", "替身回答必须明确标注。", 502)

    async def explain(self, request: m.ExplanationRequest) -> m.ExplanationResult:
        require(bool(request.question.strip()), "INVALID_QUESTION", "request", "请输入问题。")
        previous = self.store.begin(request)
        if previous:
            return previous
        self.active[request.request_id] = asyncio.current_task()
        try:
            async with asyncio.timeout(self.timeout_seconds):
                result = await self._explain(request)
                self.store.complete(result)
                return result
        except asyncio.CancelledError as exc:
            self.store.fail(request.request_id, "CANCELLED")
            raise LearningError("CANCELLED", "request", "请求已取消，未保存迟到讲解。", 409) from exc
        except TimeoutError as exc:
            self.store.fail(request.request_id)
            raise LearningError("PROVIDER_TIMEOUT", "request", "讲解超时，请检查模块连接后重试。", 504,
                                retryable=True) from exc
        except ValidationError as exc:
            self.store.fail(request.request_id)
            raise LearningError("MODEL_OUTPUT_INVALID", "request", "返回内容不符合公共协议。", 502) from exc
        except Exception:
            self.store.fail(request.request_id)
            raise
        finally:
            self.active.pop(request.request_id, None)

    async def _explain(self, request: m.ExplanationRequest) -> m.ExplanationResult:
        session = self.store.session(request.session_id)
        context = session.context.model_copy(deep=True)
        current = await self.context(context.document_id, m.ContextRequest(
            document_revision=context.document_revision, unit_id=context.unit_id,
            selected_text=context.selected_text, selected_text_hash=context.selected_text_hash,
            selection_locator=context.selection_locator))
        require(current == context, "DOCUMENT_VERSION_MISMATCH", "document",
                "服务端文档内容已变化，请重新选择当前文档。", 409)
        self.store.check_request(request.request_id)
        require(context.coverage != "NO_EXTRACTABLE_TEXT", "NO_EXTRACTABLE_TEXT", "document",
                "当前页可以阅读，但没有可用于讲解的文本。")
        conversation, sources, observations, warnings = [], [], [], []
        if request.continue_from:
            require(request.continue_from in session.explanation_ids, "DOCUMENT_VERSION_MISMATCH",
                    "session", "追问不属于当前冻结上下文。", 409)
            index = session.explanation_ids.index(request.continue_from)
            for explanation_id in session.explanation_ids[max(0, index - 5):index + 1]:
                previous = self.store.explanation(request.session_id, explanation_id)
                require(previous.context_revision == request.context_revision,
                        "DOCUMENT_VERSION_MISMATCH", "session", "追问版本已变化。", 409)
                conversation.append(previous.explanation)
            if not request.source_ids:
                previous = self.store.explanation(request.session_id, request.continue_from)
                sources = await self.existing_sources(request.session_id,
                                                      previous.explanation.code_source_ids, request.scope)
        capability = await self.provider_capability(self.providers.tutor, "tutor")
        plan = m.TeachingPlan.model_validate(await self.call(
            "tutor", self.providers.tutor.plan, context.model_copy(deep=True), request.question.strip(),
            request.level, deepcopy(conversation)))
        self.store.check_request(request.request_id)
        require(plan.question == request.question.strip() and plan.level == request.level
                and plan.mode == capability.mode and plan.status == "READY",
                "MODEL_OUTPUT_INVALID", "tutor", "教学计划改变了问题、难度或执行模式。", 502)
        if request.source_ids:
            sources = await self.existing_sources(request.session_id, request.source_ids, request.scope)
        elif request.candidate_ids:
            require(request.query_id is not None, "SOURCE_MISMATCH", "sources", "候选缺少检索 ID。")
            query, _, scope_hash = self.store.query(request.session_id, request.query_id)
            require(scope_hash == self.scope_hash(request.scope), "SOURCE_MISMATCH", "sources",
                    "候选的授权范围已变化。", 409)
            require(len(set(request.candidate_ids)) == len(request.candidate_ids)
                    and len(request.candidate_ids) <= request.scope.max_sources,
                    "SOURCE_MISMATCH", "sources", "候选数量超过解释上限。")
            for candidate_id in request.candidate_ids:
                source = await self.verify(m.VerifyRequest(session_id=request.session_id,
                                                          query_id=query.query_id, candidate_id=candidate_id))
                if self.usable(source):
                    sources.append(source)
                elif len(observations) < 3:
                    observations.append(source)
                    warnings.append("LICENSE_UNKNOWN" if source.license_observation.status != "DETECTED"
                                    else "NO_RELEVANT_SOURCE")
        elif plan.needs_code and not sources:
            terms = plan.source_query.concept_terms if plan.source_query else plan.concepts
            try:
                result = await self.search(m.SearchRequest(session_id=request.session_id,
                    context_revision=request.context_revision, question=request.question,
                    concept_terms=terms, scope=request.scope))
                self.store.check_request(request.request_id)
                if result.selection_required:
                    return m.ExplanationResult(mode=result.mode, request_id=request.request_id,
                        session_id=request.session_id, context_revision=request.context_revision,
                        status="NEEDS_SOURCE_SELECTION", candidates=result.candidates, query_id=result.query_id)
                for candidate in result.candidates:
                    if len(sources) >= request.scope.max_sources:
                        break
                    source = await self.verify(m.VerifyRequest(session_id=request.session_id,
                        query_id=result.query_id, candidate_id=candidate.candidate_id))
                    self.store.check_request(request.request_id)
                    if self.usable(source):
                        sources.append(source)
                    else:
                        if len(observations) < 3:
                            observations.append(source)
                        warnings.append("LICENSE_UNKNOWN" if source.license_observation.status != "DETECTED"
                                        else "NO_RELEVANT_SOURCE")
            except LearningError as exc:
                # A source gap can yield a truthful document-only explanation. Integrity,
                # authorization and network/model failures are never silently downgraded.
                if exc.code != "NO_RELEVANT_SOURCE":
                    raise
                warnings.append(exc.code)
        if request.compare:
            require(len({(s.repository_url, s.local_handle) for s in sources}) >= 2,
                    "NO_RELEVANT_SOURCE", "sources", "尚无两个不同仓库的核验证据，无法进行真实比较。")
        if not sources:
            warnings.append("NO_VERIFIED_CODE")
        plan.uncertainties = plan.uncertainties + list(dict.fromkeys(warnings))
        answer = m.GroundedExplanation.model_validate(await self.call(
            "tutor", self.providers.tutor.explain, context.model_copy(deep=True), deepcopy(sources),
            plan.model_copy(deep=True), deepcopy(conversation), compare=request.compare))
        self.store.check_request(request.request_id)
        self.validate_answer(answer, context, sources, plan, request.compare, capability.mode)
        used = [source for source in sources if source.source_id in answer.code_source_ids]
        return m.ExplanationResult(mode=answer.mode, request_id=request.request_id,
            session_id=request.session_id, context_revision=request.context_revision, status="COMPLETE",
            explanation=answer, sources=used, source_observations=observations,
            warnings=list(dict.fromkeys(warnings)))

    async def close(self):
        tasks = list(self.active.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(*(provider.close() for provider in (
            self.providers.document, self.providers.sources, self.providers.tutor)), return_exceptions=True)
