"use client";

import { useTransition, useState } from "react";
import type { Settings } from "@/lib/api";
import { updateSettingsAction } from "@/app/actions";

const COMMON_TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Anchorage",
  "Pacific/Honolulu",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Australia/Sydney",
];

export function SettingsForm({ settings }: { settings: Settings }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function handleSubmit(formData: FormData) {
    setError(null);
    setSaved(false);
    startTransition(async () => {
      const result = await updateSettingsAction(formData);
      if (result.error) {
        setError(result.error);
      } else {
        setSaved(true);
      }
    });
  }

  return (
    <form
      action={handleSubmit}
      className="flex flex-col gap-4 p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Study window start
          <input
            name="day_start"
            type="time"
            defaultValue={settings.day_start}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Study window end
          <input
            name="day_end"
            type="time"
            defaultValue={settings.day_end}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
      </div>

      <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
        Timezone (IANA name)
        <input
          name="timezone"
          list="timezone-options"
          defaultValue={settings.timezone}
          required
          className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
        />
        <datalist id="timezone-options">
          {COMMON_TIMEZONES.map((tz) => (
            <option key={tz} value={tz} />
          ))}
        </datalist>
      </label>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Max continuous minutes per subject
          <input
            name="max_continuous_minutes"
            type="number"
            min="1"
            defaultValue={settings.max_continuous_minutes}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Max subjects per day
          <input
            name="max_subjects_per_day"
            type="number"
            min="1"
            defaultValue={settings.max_subjects_per_day}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Scheduling lookahead (days)
          <input
            name="lookahead_days"
            type="number"
            min="1"
            defaultValue={settings.lookahead_days}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
      </div>

      <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
        How do you want to record how long tasks actually took?
        <select
          name="time_tracking_mode"
          defaultValue={settings.time_tracking_mode}
          className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
        >
          <option value="manual">Manual — type in the minutes when I complete a task</option>
          <option value="automatic">Automatic — start/pause a timer while I work</option>
        </select>
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="w-full sm:w-auto bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
        >
          {pending ? "Saving…" : "Save settings"}
        </button>
        {saved && !pending && (
          <span className="text-sm text-green-600 dark:text-green-400">Saved.</span>
        )}
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  );
}
