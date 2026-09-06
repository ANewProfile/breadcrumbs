"use client";

import { useState, useTransition } from "react";
import type { NoGoZone } from "@/lib/api";
import { createNoGoZoneAction, deleteNoGoZoneAction } from "@/app/actions";
import { InfoTooltip } from "./InfoTooltip";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function describeRecurrence(zone: NoGoZone): string {
  if (zone.date) {
    return new Date(`${zone.date}T00:00:00`).toLocaleDateString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }
  if (!zone.days_of_week || zone.days_of_week.length === 0) return "Every day";
  return zone.days_of_week
    .slice()
    .sort((a, b) => a - b)
    .map((d) => DAY_LABELS[d])
    .join(", ");
}

export function NoGoZonesForm({ zones }: { zones: NoGoZone[] }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [recurrence, setRecurrence] = useState<"days" | "date">("days");

  function handleSubmit(formData: FormData) {
    setError(null);
    startTransition(async () => {
      const result = await createNoGoZoneAction(formData);
      if (result.error) {
        setError(result.error);
      }
    });
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm mt-6">
      <div>
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 inline-flex items-center gap-1">
          No-go zones
          <InfoTooltip text="Times the scheduler will never place a task over — e.g. lunch every day, or a one-off appointment." />
        </h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
          Recurring by weekday, or a specific date.
        </p>
      </div>

      {zones.length > 0 && (
        <ul className="flex flex-col gap-2">
          {zones.map((zone) => (
            <li
              key={zone.id}
              className="flex items-center justify-between gap-3 text-sm bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2"
            >
              <div className="min-w-0">
                <p className="font-medium text-zinc-900 dark:text-zinc-100 truncate">{zone.label}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {zone.start_time}–{zone.end_time} · {describeRecurrence(zone)}
                </p>
              </div>
              <form action={deleteNoGoZoneAction}>
                <input type="hidden" name="id" value={zone.id} />
                <button
                  type="submit"
                  className="text-xs bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 px-3 py-1.5 rounded-lg hover:bg-red-100 hover:text-red-700 dark:hover:bg-red-950 dark:hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-400 transition-colors"
                >
                  Delete<span className="sr-only"> {zone.label}</span>
                </button>
              </form>
            </li>
          ))}
        </ul>
      )}

      <form action={handleSubmit} className="flex flex-col gap-3 pt-2 border-t border-zinc-200 dark:border-zinc-700">
        <div className="flex flex-col sm:flex-row gap-2">
          <label className="flex-1 flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
            <span className="sr-only">Label</span>
            <input
              name="label"
              type="text"
              required
              placeholder="Label (e.g. Lunch)"
              className="w-full bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
            <span className="sr-only">Start time</span>
            <input
              name="start_time"
              type="time"
              required
              className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
            <span className="sr-only">End time</span>
            <input
              name="end_time"
              type="time"
              required
              className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </label>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <div className="flex items-center gap-3 text-xs text-zinc-600 dark:text-zinc-300">
            <label className="inline-flex items-center gap-1.5">
              <input
                type="radio"
                name="recurrence"
                value="days"
                checked={recurrence === "days"}
                onChange={() => setRecurrence("days")}
              />
              Recurring
            </label>
            <label className="inline-flex items-center gap-1.5">
              <input
                type="radio"
                name="recurrence"
                value="date"
                checked={recurrence === "date"}
                onChange={() => setRecurrence("date")}
              />
              Specific date
            </label>
          </div>

          {recurrence === "days" ? (
            <div className="flex flex-wrap gap-2">
              {DAY_LABELS.map((label, i) => (
                <label
                  key={label}
                  className="inline-flex items-center gap-1 text-xs text-zinc-600 dark:text-zinc-300"
                >
                  <input type="checkbox" name="days_of_week" value={i} />
                  {label}
                </label>
              ))}
              <span className="text-xs text-zinc-400 dark:text-zinc-500">(none checked = every day)</span>
            </div>
          ) : (
            <input
              name="date"
              type="date"
              required
              className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          )}
        </div>

        <button
          type="submit"
          disabled={pending}
          className="self-start text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
        >
          {pending ? "Adding…" : "Add no-go zone"}
        </button>
        {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>
    </div>
  );
}
