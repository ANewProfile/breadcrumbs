"use client";

import { useState, useTransition } from "react";
import { addSnowDayAction } from "@/app/actions";

const inputClass =
  "bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500";

export function AddSnowDayAction() {
  const [snowDate, setSnowDate] = useState("");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function handleSubmit() {
    setError(null);
    setMessage(null);
    startTransition(async () => {
      const result = await addSnowDayAction(snowDate);
      if (result.error) {
        setError(result.error);
      } else {
        setMessage(result.message ?? "Done.");
        setSnowDate("");
      }
    });
  }

  return (
    <section className="p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
        Snow day
      </h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
        Removes school for that date and shifts every later day back to fill the gap — Day 3
        just happens on the next school day instead of being skipped.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="date"
          value={snowDate}
          onChange={(e) => setSnowDate(e.target.value)}
          aria-label="Snow day date"
          className={`${inputClass} sm:w-48`}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={pending || !snowDate}
          className="bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
        >
          {pending ? "Adding snow day…" : "Add snow day"}
        </button>
      </div>
      {message && (
        <p role="status" className="mt-3 text-sm text-green-600 dark:text-green-400">
          {message}
        </p>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
    </section>
  );
}
