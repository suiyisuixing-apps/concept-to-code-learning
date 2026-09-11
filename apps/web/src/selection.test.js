import { expect, test } from "vitest";
import { captureBlocks, mapPdfQuote, questionForSelection } from "./selection.js";

const unit = { blocks: [{ block_id: "first", text: "A😀保留零值" }, { block_id: "second", text: "第二段文字" }] };
test("dragging through Unicode and nested marks captures exact ordered spans", () => {
  const first = document.createElement("p"), second = document.createElement("p");
  first.innerHTML = "A<mark>😀保留</mark>零值"; second.textContent = "第二段文字";
  document.body.append(first, second);
  const range = document.createRange(); range.setStart(first.firstChild, 1); range.setEnd(second.firstChild, 2);
  const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  const value = captureBlocks(unit, new Map([["first", first], ["second", second]]));
  expect(value).toEqual({ text: "😀保留零值\n第二", spans: [{ block_id: "first", start: 1, end: 6 }, { block_id: "second", start: 0, end: 2 }] });
  range.setEnd(document.body, 2); selection.removeAllRanges(); selection.addRange(range);
  expect(captureBlocks(unit, new Map([["first", first], ["second", second]]))).toBeNull();
  first.remove(); second.remove(); selection.removeAllRanges();
});
test("PDF whitespace differences resolve to original server text", () => {
  const source = { blocks: [{ block_id: "paragraph", text: "Gradient\n  descent 😀" }] };
  expect(mapPdfQuote(source, "Gradient descent 😀", 0, 18)).toEqual({
    text: "Gradient\n  descent 😀", spans: [{ block_id: "paragraph", start: 0, end: 20 }],
  });
});
test("PDF repeated quotes use their page position and ambiguous matches fail closed", () => {
  const repeated = { blocks: [{ block_id: "first", text: "同一句" }, { block_id: "second", text: "同一句" }] };
  expect(mapPdfQuote(repeated, "同一句同一句", 3, 6)).toEqual({ text: "同一句", spans: [{ block_id: "second", start: 0, end: 3 }] });
  expect(mapPdfQuote(repeated, "同一句", 0, 3)).toBeNull();
});
test("large editable prompts stay bounded without splitting emoji", () => {
  const text = "😀".repeat(5000);
  const prompt = questionForSelection({ text });
  expect(prompt.length).toBeLessThan(2000);
  expect(prompt.endsWith("😀…")).toBe(true);
});
