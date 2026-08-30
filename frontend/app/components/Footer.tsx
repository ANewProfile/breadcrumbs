import Link from "next/link";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800 mt-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-zinc-500 dark:text-zinc-400">
        <p>
          &copy; {year} Theodore Chen. Breadcrumbs is operated by Theodore
          Chen.
        </p>
        <nav aria-label="Legal">
          <ul className="flex items-center gap-4">
            <li>
              <Link
                href="/privacy"
                className="hover:text-zinc-700 dark:hover:text-zinc-200 underline underline-offset-2 transition-colors"
              >
                Privacy Policy
              </Link>
            </li>
            <li>
              <Link
                href="/terms"
                className="hover:text-zinc-700 dark:hover:text-zinc-200 underline underline-offset-2 transition-colors"
              >
                Terms of Service
              </Link>
            </li>
            <li>
              <a
                href="mailto:theochen16@gmail.com"
                className="hover:text-zinc-700 dark:hover:text-zinc-200 underline underline-offset-2 transition-colors"
              >
                Contact
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
