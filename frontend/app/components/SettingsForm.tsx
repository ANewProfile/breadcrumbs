"use client";

import { useTransition, useState } from "react";
import type { Settings, Calendar } from "@/lib/api";
import { updateSettingsAction } from "@/app/actions";
import { InfoTooltip } from "./InfoTooltip";

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

export function SettingsForm({
  settings,
  calendars,
}: {
  settings: Settings;
  calendars: Calendar[];
}) {
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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="inline-flex items-center gap-1">
            Max continuous minutes per subject
            <InfoTooltip text="The longest stretch the scheduler will assign to one subject in a row before switching, based on cognitive-load research on interleaving." />
          </span>
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
          <span className="inline-flex items-center gap-1">
            Max subjects per day
            <InfoTooltip text="Caps how many different subjects get scheduled in one day, so your day isn't fragmented across too many topics." />
          </span>
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
          <span className="inline-flex items-center gap-1">
            Max productive minutes per day
            <InfoTooltip text="The scheduler packs each day toward this limit — getting tasks done as soon as possible — before it ever spills work onto a later day." />
          </span>
          <input
            name="max_daily_minutes"
            type="number"
            min="1"
            defaultValue={settings.max_daily_minutes}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="inline-flex items-center gap-1">
            Scheduling lookahead (days)
            <InfoTooltip text="How many days ahead the scheduler looks when placing tasks into your free time." />
          </span>
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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="inline-flex items-center gap-1">
            Break between tasks (minutes)
            <InfoTooltip text="A gap the scheduler leaves between two back-to-back tasks in the same subject." />
          </span>
          <input
            name="break_between_tasks_minutes"
            type="number"
            min="0"
            defaultValue={settings.break_between_tasks_minutes}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="inline-flex items-center gap-1">
            Break between subjects (minutes)
            <InfoTooltip text="A gap the scheduler leaves whenever it switches from one subject to another." />
          </span>
          <input
            name="break_between_subjects_minutes"
            type="number"
            min="0"
            defaultValue={settings.break_between_subjects_minutes}
            required
            className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          />
        </label>
      </div>

      <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
        <span className="inline-flex items-center gap-1">
          How do you want to record how long tasks actually took?
          <InfoTooltip text="Used to compare against your estimates and improve future time predictions for similar tasks." />
        </span>
        <select
          name="time_tracking_mode"
          defaultValue={settings.time_tracking_mode}
          className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
        >
          <option value="manual">Manual — type in the minutes when I complete a task</option>
          <option value="automatic">Automatic — start/pause a timer while I work</option>
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
        <span className="inline-flex items-center gap-1">
          Preferred time of day
          <InfoTooltip text="Being willing to work at 6:30am doesn't mean you'd rather do it then than at 3:30pm. The scheduler will try to fit tasks into this window first, and only spill into the rest of your study window when it's full." />
        </span>
        <select
          name="preferred_time_of_day"
          defaultValue={settings.preferred_time_of_day}
          className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
        >
          <option value="no_preference">No preference</option>
          <option value="morning">Morning (before 12pm)</option>
          <option value="afternoon">Afternoon (12pm–5pm)</option>
          <option value="evening">Evening (after 5pm)</option>
        </select>
      </label>

      {calendars.length > 0 && (
        <fieldset className="flex flex-col gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <input type="hidden" name="has_calendar_options" value="1" />
          <legend className="inline-flex items-center gap-1 px-0">
            Calendars to treat as busy time
            <InfoTooltip text="Includes calendars shared with you and ones you've subscribed to, not just your own. Unchecked calendars are ignored when the scheduler looks for free time." />
          </legend>
          <div className="flex flex-col gap-1.5">
            {calendars.map((cal) => (
              <label
                key={cal.id}
                className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300"
              >
                <input
                  type="checkbox"
                  name="selected_calendar_ids"
                  value={cal.id}
                  defaultChecked={settings.selected_calendar_ids.includes(cal.id)}
                  className="rounded border-zinc-300 dark:border-zinc-600 text-indigo-600 focus:ring-indigo-400"
                />
                {cal.summary}
                {cal.primary && (
                  <span className="text-xs text-zinc-400 dark:text-zinc-500">(primary)</span>
                )}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="w-full sm:w-auto bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
        >
          {pending ? "Saving…" : "Save settings"}
        </button>
        {saved && !pending && (
          <span role="status" className="text-sm text-green-600 dark:text-green-400">Saved.</span>
        )}
      </div>

      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  );
}
