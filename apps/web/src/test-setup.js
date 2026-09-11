import "@testing-library/jest-dom/vitest";
import { webcrypto } from "node:crypto";
import { TextEncoder } from "node:util";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { JSDOM } from "jsdom";

Object.defineProperty(globalThis, "crypto", {
  value: webcrypto,
  configurable: true,
});
globalThis.TextEncoder = TextEncoder;
// Use DOM storage rather than Node 25+ experimental host storage in browser tests.
const storageWindow = new JSDOM("", { url: "http://127.0.0.1" }).window;
for (const key of ["localStorage", "sessionStorage"]) {
  Object.defineProperty(window, key, { value: storageWindow[key], configurable: true });
}
afterEach(cleanup);

beforeEach(() => { window.localStorage.clear(); window.sessionStorage.clear(); });
