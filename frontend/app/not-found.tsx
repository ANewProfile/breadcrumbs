import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "./components/Breadcrumbs";

export const metadata: Metadata = {
  title: "Page not found",
  description: "The page you're looking for doesn't exist or may have moved.",
};

export default function NotFound() {
  return (
    <main id="main-content" className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Page not found" }]} />

      <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mb-1">
        Page not found
      </h1>
      <p className="text-sm sm:text-base text-zinc-500 dark:text-zinc-400 mb-6">
        The page you&rsquo;re looking for doesn&rsquo;t exist or may have moved.
      </p>

      <div className="flex flex-wrap gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg transition-colors"
        >
          Go home
        </Link>
        <Link
          href="/settings"
          className="inline-flex items-center gap-2 text-sm font-medium text-zinc-600 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 px-4 py-2 rounded-lg transition-colors"
        >
          Settings
        </Link>
        <Link
          href="/privacy"
          className="inline-flex items-center gap-2 text-sm font-medium text-zinc-600 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 px-4 py-2 rounded-lg transition-colors"
        >
          Privacy Policy
        </Link>
        <Link
          href="/terms"
          className="inline-flex items-center gap-2 text-sm font-medium text-zinc-600 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 px-4 py-2 rounded-lg transition-colors"
        >
          Terms of Service
        </Link>
      </div>
    </main>
  );
}
