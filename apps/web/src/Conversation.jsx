import { useEffect, useRef } from "react";

function Prose({ text }) {
  return text.split(/(`[^`\n]+`)/g).map((part, index) => part.startsWith("`") && part.endsWith("`")
    ? <code className="inline-code" key={index}>{part.slice(1, -1)}</code> : part);
}

export function SourceCard({ source, expanded = true }) {
  const repository = source.repository_owner ? `${source.repository_owner}/${source.repository_name}` : "本地仓库";
  return <article className="source-card">
    <header><strong>{repository}</strong>{source.permalink && <a href={source.permalink} target="_blank" rel="noreferrer">查看源码 ↗</a>}</header>
    <p className="code-location">{source.file_path} · L{source.line_start}–{source.line_end}</p>
    {source.code_excerpt ? <details className="code-disclosure" open={expanded}><summary>{source.symbol || "代码片段"}</summary><pre aria-label="已核验原始代码"><code>{source.code_excerpt}</code></pre></details>
      : <p>未取得明确的代码许可，暂不展示片段。</p>}
    <details className="source-details"><summary>版本与许可 · {source.execution_status === "NOT_RUN" ? "未运行" : source.execution_status}</summary>
      <dl><dt>{source.dirty ? "当前文件" : "Commit"}</dt><dd><code>{source.dirty ? source.file_sha256 : source.commit_sha || source.file_sha256}</code></dd><dt>核验</dt><dd>{source.verification_status}</dd><dt>许可</dt><dd>{source.license_observation.files?.map((file) => <div key={file.path}>{file.permalink ? <a href={file.permalink} target="_blank" rel="noreferrer">{file.identifier || "未识别"} · {file.path}</a> : file.identifier || "未识别"}</div>)}</dd></dl>
      <p>{source.relevance.reason}</p></details>
  </article>;
}

export default function Conversation({ turns, current, noteText, setNoteText, saving, saveNote, preview, pendingQuestion }) {
  const container = useRef(null), follow = useRef(true);
  useEffect(() => { const node = container.current; if (node && follow.current && preview?.length) node.scrollTop = node.scrollHeight; }, [preview]);
  return <div ref={container} className="conversation" aria-label="学习对话" onScroll={(event) => { const node = event.currentTarget; follow.current = node.scrollHeight - node.scrollTop - node.clientHeight < 120; }}>{!turns.length && !pendingQuestion && <p className="conversation-empty">想理解哪一部分？</p>}
    {turns.map((turn, turnIndex) => {
      const answer = turn.explanation;
      if (!answer) return null;
      const selected = current?.explanation_id === answer.explanation_id;
      return <article className="conversation-turn" key={answer.explanation_id}>
        <div className="user-message"><span>{answer.context_snapshot?.file_name} · {answer.context_snapshot?.unit_locator?.index || "当前选区"}</span><p>{answer.question}</p></div>
        <div className="answer">
          {answer.status === "FIXTURE" && <p className="answer-status">演示回答</p>}
          {answer.answer_sections.map((section, i) => <section key={i}><h3>{section.title}</h3><p><Prose text={section.text}/></p></section>)}
          {answer.comparison && <section><h3>实现比较</h3><p>{answer.comparison.summary}</p><ul>{answer.comparison.tradeoffs.map((text, i) => <li key={i}>{text}</li>)}</ul></section>}
          {turn.sources?.map((source) => <div key={source.source_id}><SourceCard source={source} expanded={!turns.slice(0, turnIndex).some((previous) => previous.sources?.some((item) => item.source_id === source.source_id))}/></div>)}
          {answer.example_blocks.filter((item) => item.provenance_kind !== "SOURCE_EXACT").map((item, index) => <section key={index}><h3>{item.provenance_kind === "ADAPTED_FROM_SOURCE" ? "改编示例" : "AI 生成示例"} · 未运行</h3><pre><code>{item.code}</code></pre><p>{item.explanation}</p></section>)}
          <details className="answer-details"><summary>引用与回答信息</summary>{answer.document_citations.map((item, i) => <blockquote key={i}>{item.quote}</blockquote>)}
            {answer.concept_code_links.map((link, i) => <p key={`link-${i}`}><strong>{link.concept}</strong>：{link.reason}</p>)}
            {answer.limitations.map((text, i) => <p key={i}>{text}</p>)}
            <p>{answer.provider_info.model_id?.split(/[\\/]/).at(-1) || "测试模型"} · 模型用时 {(answer.metrics.latency_ms / 1000).toFixed(1)} 秒</p>
            <p>输入 {answer.metrics.input_tokens ?? "未知"} / 输出 {answer.metrics.output_tokens ?? "未知"} tokens · {answer.metrics.token_source === "PROVIDER_USAGE" ? "模型报告" : "估算"}</p>
            {answer.metrics.input_truncated && <p>{answer.metrics.truncation_reason}</p>}
          </details>
          {selected && <details className="save-note"><summary>保存为笔记</summary><label>我的理解<textarea aria-label="我的理解" maxLength={20000} value={noteText} onChange={(e) => setNoteText(e.target.value)}/></label><button disabled={saving} onClick={saveNote}>{saving ? "保存中…" : "保存笔记"}</button></details>}
        </div>
      </article>;
    })}
    {pendingQuestion && <article className="conversation-turn" aria-label="正在生成的回答" aria-busy="true"><div className="user-message"><p>{pendingQuestion}</p></div><div className="answer">{preview?.map((section, i) => <section key={i}><h3>{section.title}</h3><p><Prose text={section.text}/></p></section>)}</div></article>}
  </div>;
}
