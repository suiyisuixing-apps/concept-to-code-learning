export async function api(path, body) {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error("服务响应无法读取，请确认本地服务已启动。");
  }
  if (!response.ok) {
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : result.message || "请求未完成，请检查输入后重试。",
    );
  }
  return result;
}

export async function hashText(text) {
  if (!text) return null;
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(text),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}
