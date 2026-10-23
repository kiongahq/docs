import { JSDOM } from "jsdom";
import fs from "node:fs"; import path from "node:path";
const dom = new JSDOM("<!doctype html><body></body>");
globalThis.window = dom.window; globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.DOMParser = dom.window.DOMParser; globalThis.Element = dom.window.Element; globalThis.HTMLElement = dom.window.HTMLElement;
const { default: mermaid } = await import("mermaid");
mermaid.initialize({ startOnLoad: false });
let bad = 0, total = 0;
function* walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) yield* walk(p); else if (p.endsWith(".md")) yield p; } }
// Parses every ```mermaid block with Mermaid itself; a syntax error renders
// as raw text on the published site.
for (const root of process.argv.slice(2)) for (const f of walk(root)) {
  const re = /```mermaid\n([\s\S]*?)```/g; let m;
  const text = fs.readFileSync(f, "utf8");
  while ((m = re.exec(text))) { total++; try { await mermaid.parse(m[1]); } catch (e) { bad++; console.log(`${f}: ${String(e.message || e).split("\n").slice(0,3).join(" | ")}`); } }
}
console.log(`${total} diagrams, ${bad} invalid`);
process.exit(bad ? 1 : 0);
