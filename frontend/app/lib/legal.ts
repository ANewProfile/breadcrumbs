import fs from "node:fs";
import path from "node:path";
import { Marked, type RendererObject, type Tokens } from "marked";

// Source of truth for legal copy lives in /legal at the repo root, not here.
// These pages render whatever is in those files so the site can't drift from them.
const LEGAL_DIR = path.join(process.cwd(), "..", "legal");

const styles = {
  h2: "text-lg font-semibold text-zinc-900 dark:text-zinc-100 mt-8 mb-2",
  p: "text-sm sm:text-base text-zinc-700 dark:text-zinc-300 leading-relaxed",
  ul: "list-disc pl-6 text-sm sm:text-base text-zinc-700 dark:text-zinc-300 leading-relaxed space-y-1",
  a: "text-indigo-600 dark:text-indigo-400 underline underline-offset-2 hover:text-indigo-500",
};

const LEGAL_DOC_ROUTES: Record<string, string> = {
  "terms-of-service.md": "/terms",
  "privacy-policy.md": "/privacy",
};

function resolveHref(href: string): string {
  const bare = href.replace(/^\.\//, "");
  return LEGAL_DOC_ROUTES[bare] ?? href;
}

function createRenderer(): RendererObject {
  const renderer: RendererObject = {
    heading({ tokens, depth }: Tokens.Heading) {
      const text = this.parser.parseInline(tokens);
      return depth === 1 ? "" : `<h${depth} class="${styles.h2}">${text}</h${depth}>`;
    },
    paragraph({ tokens }: Tokens.Paragraph) {
      return `<p class="${styles.p}">${this.parser.parseInline(tokens)}</p>`;
    },
    list(token: Tokens.List) {
      const tag = token.ordered ? "ol" : "ul";
      const items = token.items.map((item) => this.listitem(item)).join("");
      return `<${tag} class="${styles.ul}">${items}</${tag}>`;
    },
    listitem(item: Tokens.ListItem) {
      return `<li>${this.parser.parse(item.tokens)}</li>`;
    },
    link({ href, tokens }: Tokens.Link) {
      const text = this.parser.parseInline(tokens);
      const resolved = resolveHref(href);
      const external = /^https?:\/\//.test(resolved);
      const extraAttrs = external ? ' target="_blank" rel="noopener noreferrer"' : "";
      return `<a class="${styles.a}" href="${resolved}"${extraAttrs}>${text}</a>`;
    },
  };
  return renderer;
}

export type LegalDoc = {
  title: string;
  effectiveDate: string;
  html: string;
};

type LegalFileName = "terms-of-service.md" | "privacy-policy.md";

export function getLegalDoc(fileName: LegalFileName): LegalDoc {
  const raw = fs.readFileSync(path.join(LEGAL_DIR, fileName), "utf8");

  const titleMatch = raw.match(/^#\s+(.+?)\s*\n/);
  const title = titleMatch?.[1] ?? "";
  let rest = titleMatch ? raw.slice(titleMatch[0].length) : raw;

  const dateMatch = rest.match(/^\s*\n?\*\*Effective date:\*\*\s*(.+?)\s*\n/);
  const effectiveDate = dateMatch?.[1] ?? "";
  rest = dateMatch ? rest.slice(dateMatch.index! + dateMatch[0].length) : rest;

  const marked = new Marked({ renderer: createRenderer() });
  const html = marked.parse(rest, { async: false }) as string;

  return { title, effectiveDate, html };
}
