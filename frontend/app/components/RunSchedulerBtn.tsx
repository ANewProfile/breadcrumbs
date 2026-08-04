"use client";

import { useTransition, useState } from "react";
import { runSchedulerAction } from "@/app/actions";

export function RunSchedulerBtn() {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleClick() {
    setError(null);
    startTransition(async () => {
      const result = await runSchedulerAction();
      if (result.error) setError(result.error);
    });
  }

  return (
    <div className="mb-6 sm:mb-8">
      <button
        onClick={handleClick}
        disabled={pending}
        className="w-full sm:w-auto flex items-center justify-center gap-2 bg-indigo-600 text-white text-sm font-medium px-5 py-2.5 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className={`w-4 h-4 ${pending ? "animate-spin" : ""}`}
          aria-hidden="true"
        >
          <path
            d="M4 4v5h5M20 20v-5h-5M5.5 9a7 7 0 0 1 12.6-2.3M18.5 15a7 7 0 0 1-12.6 2.3"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {pending ? "Scheduling…" : "Run Scheduler"}
      </button>
      {error && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
