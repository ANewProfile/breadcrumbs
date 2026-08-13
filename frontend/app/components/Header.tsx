import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";
import { logoutAction } from "@/app/actions";
import { BASE, type CurrentUser } from "@/lib/api";

function Logo() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className="w-6 h-6 shrink-0"
      aria-hidden="true"
    >
      <circle cx="5" cy="19" r="2.2" className="fill-indigo-300 dark:fill-indigo-800" />
      <circle cx="12" cy="12" r="2.2" className="fill-indigo-500 dark:fill-indigo-500" />
      <circle cx="19" cy="5" r="2.6" className="fill-indigo-600 dark:fill-indigo-400" />
      <path
        d="M6.6 17.6 10.4 13.8M13.6 10.4 17.4 6.6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        className="text-indigo-300 dark:text-indigo-700"
      />
    </svg>
  );
}

export function Header({ user }: { user: CurrentUser | null }) {
  return (
    <header className="sticky top-0 z-10 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-zinc-900 dark:text-zinc-100 hover:opacity-80 transition-opacity"
        >
          <Logo />
          <span>Breadcrumbs</span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-4">
          {user ? (
            <>
              <Link
                href="/settings"
                className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
              >
                Settings
              </Link>
              <span className="hidden sm:inline text-sm text-zinc-500 dark:text-zinc-400 truncate max-w-[160px]">
                {user.email}
              </span>
              <form action={logoutAction}>
                <button
                  type="submit"
                  className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
                >
                  Sign out
                </button>
              </form>
            </>
          ) : (
            <a
              href={`${BASE}/auth/google/login`}
              className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg transition-colors"
            >
              Sign in with Google
            </a>
          )}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
