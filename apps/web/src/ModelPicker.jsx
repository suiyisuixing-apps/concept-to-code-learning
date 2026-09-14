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
  function select(id, base_url = catalog.base_url, interactive = true, ready = catalog.models.some((item) => item.id === id)) {
    setChoice(id); const value = { id, base_url };
    change({ ...value, ready }, interactive);
    if (ready) setError("");
    try { window.localStorage.setItem(KEY, JSON.stringify(value)); } catch { /* Storage can be disabled. */ }
  }
  async function discover(address, startup = false) {
    const current = ++epoch.current; setLoading(true); setError("");
    change({ id: choice, base_url: address || null, ready: false }, !startup);
    try {
      const value = await api(address ? "/models/discover" : "/models", address ? json("POST", { base_url: address }) : {});
      if (epoch.current !== current) return;
      const models = Array.isArray(value.models) ? value.models.filter((item) => typeof item?.id === "string" && item.id) : [];
      setCatalog({ ...value, models });
      setEndpoint(value.base_url || address || "");
      const retained = startup ? initial.current?.id : choice;
      const selected = retained || value.default_model || models[0]?.id || "";
      select(selected, value.base_url || address || null, !startup, models.some((item) => item.id === selected));
      if (!models.some((item) => item.id === selected) && selected) setError("所选模型当前不可用，请重新选择。");
      if (!models.length) setError(value.needed_action || "没有可用模型，请检查模型服务。");
      if (!startup && models.length) setEditing(false);
    } catch (e) { if (epoch.current === current) setError(e.message); }
    finally { if (epoch.current === current) setLoading(false); }
  }
  useEffect(() => {
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
