import { useEffect, useRef, useState } from "react";
import { api, json } from "./api.js";

const KEY = "c2c-model-choice";
function saved() { try { return JSON.parse(window.localStorage.getItem(KEY) || "null"); } catch { return null; } }

export default function ModelPicker({ change, disabled }) {
  const initial = useRef(saved());
  const [catalog, setCatalog] = useState({ models: [] });
  const [choice, setChoice] = useState(initial.current?.id || "");
  const [endpoint, setEndpoint] = useState(initial.current?.base_url || "");
  const [editing, setEditing] = useState(false), [loading, setLoading] = useState(true), [error, setError] = useState("");
  const epoch = useRef(0);
  function select(id, base_url = catalog.base_url, interactive = true) {
    setChoice(id); const value = { id, base_url };
    change(value, interactive);
    try { window.localStorage.setItem(KEY, JSON.stringify(value)); } catch { /* Storage can be disabled. */ }
  }
  async function discover(address, startup = false) {
    const current = ++epoch.current; setLoading(true); setError("");
    try {
      const value = await api(address ? "/models/discover" : "/models", address ? json("POST", { base_url: address }) : {});
      if (epoch.current !== current) return;
      const models = value.models || []; setCatalog({ ...value, models });
      setEndpoint(value.base_url || address || "");
      const selected = startup && initial.current?.id || value.default_model || models[0]?.id || "";
      select(selected, value.base_url || address || null, !startup);
      if (!models.some((item) => item.id === selected) && selected) setError("所选模型当前不可用，请重新选择。");
      if (!startup && models.length) setEditing(false);
    } catch (e) { if (epoch.current === current) setError(e.message); }
    finally { if (epoch.current === current) setLoading(false); }
  }
  useEffect(() => {
    if (initial.current?.id) change(initial.current, false);
    discover(initial.current?.base_url, true);
    return () => { epoch.current++; };
  }, []);
  return <div className="model-picker">
    <div className="model-choice"><select aria-label="选择模型" value={choice} disabled={disabled || loading} onChange={(e) => select(e.target.value)}>
      {!catalog.models.length && <option value={choice}>{loading ? "连接模型…" : "选择模型"}</option>}
      {choice && catalog.models.length > 0 && !catalog.models.some((item) => item.id === choice) && <option value={choice}>所选模型不可用</option>}
      {catalog.models.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
    </select><button className="quiet-button" disabled={disabled} aria-expanded={editing} onClick={() => setEditing(!editing)}>模型设置</button></div>
    {editing && <div className="model-settings"><label>本地模型服务<input aria-label="模型服务地址" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="http://127.0.0.1:11434/v1"/></label>
      <button disabled={loading || disabled} onClick={() => discover(endpoint)}>{loading ? "连接中…" : "连接"}</button>
      <small>列出服务实际提供的模型。</small></div>}
    {error && <p className="inline-error" role="alert">{error}<button onClick={() => discover(endpoint)} disabled={loading}>重试连接</button></p>}
  </div>;
}
