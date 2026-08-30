"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "breadcrumbs_cookie_consent";

export function CookieConsent() {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(window.localStorage.getItem(STORAGE_KEY) === "1");
  }, []);

  function dismiss() {
    window.localStorage.setItem(STORAGE_KEY, "1");
    setDismissed(true);
  }

  if (dismissed) return null;

  return (
    <div
      role="region"
      aria-label="Cookie notice"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/95 backdrop-blur"
    >
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center gap-3">
        <p className="text-sm text-zinc-600 dark:text-zinc-300 text-center sm:text-left">
          Breadcrumbs uses a single essential cookie to keep you signed in.
          It&rsquo;s not used for tracking or advertising. See our{" "}
          <Link
            href="/privacy"
            className="underline underline-offset-2 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            Privacy Policy
          </Link>{" "}
          for details.
        </p>
        <button
          type="button"
          onClick={dismiss}
          className="shrink-0 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-4 py-1.5 rounded-lg transition-colors"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
