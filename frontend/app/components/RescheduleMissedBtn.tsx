"use client";

import { useTransition, useState } from "react";
import { rescheduleMissedAction } from "@/app/actions";

export function RescheduleMissedBtn({ count }: { count: number }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleClick() {
    setError(null);
    startTransition(async () => {
      const result = await rescheduleMissedAction();
      if (result.error) setError(result.error);
    });
  }

  return (
    <div className="mb-6 sm:mb-8 rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950 px-4 py-3">
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
        <p className="text-sm font-medium text-amber-800 dark:text-amber-300 flex-1">
          {count} missed task{count > 1 ? "s" : ""} — the scheduled time already passed.
        </p>
        <button
          onClick={handleClick}
          disabled={pending}
          className="shrink-0 text-sm font-medium text-white bg-amber-600 hover:bg-amber-500 px-4 py-1.5 rounded-lg disabled:opacity-50 transition-colors"
        >
          {pending ? "Rescheduling…" : "Reschedule missed tasks"}
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
