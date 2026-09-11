import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// Copy the pinned dependency's fonts/decoders; no CDN or remote document uploads.
const root = new URL("../", import.meta.url);
await rm(new URL("public/pdfjs/", root), { recursive: true, force: true });
for (const name of ["cmaps", "standard_fonts", "wasm", "iccs"]) {
  const destination = new URL(`public/pdfjs/${name}/`, root);
  await mkdir(destination, { recursive: true });
  await cp(fileURLToPath(new URL(`node_modules/pdfjs-dist/${name}/`, root)),
    fileURLToPath(destination), { recursive: true });
}
const notices = [];
for (const name of ["react", "react-dom", "scheduler", "pdfjs-dist"]) {
  notices.push(name + "\n\n" + await readFile(new URL(`node_modules/${name}/LICENSE`, root), "utf8"));
}
await writeFile(new URL("public/pdfjs/THIRD_PARTY_NOTICES.txt", root), notices.join("\n\n-----\n\n"), "utf8");
