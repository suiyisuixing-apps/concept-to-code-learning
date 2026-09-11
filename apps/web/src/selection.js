// Offsets sent to the API count Unicode code points, not JavaScript UTF-16 units.
export const selectionKey = (value) => value ? JSON.stringify(value.spans) : "";

export function fromSpans(unit, spans) {
  return { spans, text: spans.map((span) => Array.from(unit.blocks.find((b) => b.block_id === span.block_id).text)
    .slice(span.start, span.end).join("")).join("\n") };
}

function offsetIn(node, container, offset) {
  const before = document.createRange();
  before.selectNodeContents(node); before.setEnd(container, offset);
  return Array.from(before.toString()).length;
}

export function captureBlocks(unit, nodes, selection = window.getSelection()) {
  if (!unit || !selection?.rangeCount || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  const roots = [...nodes.values()];
  if (!roots.some((node) => node.contains(range.startContainer))
      || !roots.some((node) => node.contains(range.endContainer))) return null;
  const spans = [];
  for (const block of unit.blocks) {
    const node = nodes.get(block.block_id);
    if (!node || !range.intersectsNode(node)) continue;
    const length = Array.from(block.text).length;
    const start = node.contains(range.startContainer) ? offsetIn(node, range.startContainer, range.startOffset) : 0;
    const end = node.contains(range.endContainer) ? offsetIn(node, range.endContainer, range.endOffset) : length;
    if (end > start && start >= 0 && end <= length) spans.push({ block_id: block.block_id, start, end });
  }
  return spans.length ? fromSpans(unit, spans) : null;
}

function normalized(text) {
  const map = []; let value = "";
  Array.from(text).forEach((char, index) => {
    const part = char.normalize("NFKC").replace(/\s/gu, "");
    value += part;
    for (let i = 0; i < part.length; i++) map.push(index);
  });
  return { value, map };
}

export function mapPdfQuote(unit, pageText, start, end) {
  const original = unit.blocks.map((b) => b.text).join("\n");
  const canonical = normalized(original), layer = normalized(pageText);
  const chars = Array.from(pageText);
  const quote = normalized(chars.slice(start, end).join("")).value;
  if (!quote) return null;
  const prefix = normalized(chars.slice(0, start).join("")).value;
  const suffix = normalized(chars.slice(end).join("")).value;
  let match = -1;
  if (canonical.value === layer.value) match = prefix.length;
  else {
    const matches = [];
    for (let at = canonical.value.indexOf(quote); at !== -1; at = canonical.value.indexOf(quote, at + 1)) matches.push(at);
    const contextual = matches.filter((at) => canonical.value.slice(0, at).endsWith(prefix.slice(-32))
      && canonical.value.slice(at + quote.length).startsWith(suffix.slice(0, 32)));
    if (matches.length === 1) match = matches[0];
    else if (contextual.length === 1) match = contextual[0];
  }
  if (match < 0) return null;
  const first = canonical.map[match], last = canonical.map[match + quote.length - 1] + 1;
  const spans = []; let position = 0;
  for (const block of unit.blocks) {
    const length = Array.from(block.text).length;
    const start = Math.max(first - position, 0), end = Math.min(last - position, length);
    if (end > start) spans.push({ block_id: block.block_id, start, end });
    position += length + 1;
  }
  return spans.length ? fromSpans(unit, spans) : null;
}

export function capturePdf(unit, root, selection = window.getSelection()) {
  if (!root || !selection?.rangeCount || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) return null;
  return mapPdfQuote(unit, root.textContent, offsetIn(root, range.startContainer, range.startOffset),
    offsetIn(root, range.endContainer, range.endOffset));
}

export function questionForSelection(value) {
  let quote = "";
  for (const char of value.text) { if (quote.length + char.length > 1600) break; quote += char; }
  return `请解释这段原文：\n${quote}${quote.length < value.text.length ? "…" : ""}`;
}
