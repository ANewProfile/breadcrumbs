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
    <div className="mb-8">
      <button
        onClick={handleClick}
        disabled={pending}
        className="bg-blue-600 text-white text-sm px-5 py-2 rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-colors"
      >
        {pending ? "Scheduling…" : "Run Scheduler"}
      </button>
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
