import "@testing-library/jest-dom/vitest";
import { webcrypto } from "node:crypto";
import { TextEncoder } from "node:util";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

Object.defineProperty(globalThis, "crypto", {
  value: webcrypto,
  configurable: true,
});
globalThis.TextEncoder = TextEncoder;
afterEach(cleanup);
