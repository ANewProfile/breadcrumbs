import Link from "next/link";

export type Crumb = { label: string; href?: string };

/** Navigational breadcrumb trail (Home / Settings / ...), not the app's name. */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={item.label} className="flex items-center gap-1.5">
              {i > 0 && (
                <span aria-hidden="true" className="text-zinc-300 dark:text-zinc-600">
                  /
                </span>
              )}
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  className="hover:text-zinc-700 dark:hover:text-zinc-200 underline underline-offset-2 transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  aria-current={isLast ? "page" : undefined}
                  className={isLast ? "text-zinc-700 dark:text-zinc-300 font-medium" : undefined}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
