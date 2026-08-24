"use client";

import { useState, useTransition } from "react";
import { generateSchoolScheduleAction } from "@/app/actions";
import type { DayNumber, EarlyDismissal } from "@/lib/api";

const inputClass =
  "bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500";

const DAY_NUMBERS: DayNumber[] = ["1", "2", "3", "4", "5", "6"];

export function GenerateCalendarForm({
  googleConnected,
  googleLoginUrl,
}: {
  googleConnected: boolean;
  googleLoginUrl: string;
}) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [startDayNumber, setStartDayNumber] = useState<DayNumber>("1");
  const [offDates, setOffDates] = useState<string[]>([]);
  const [newOffDate, setNewOffDate] = useState("");
  const [earlyDismissals, setEarlyDismissals] = useState<EarlyDismissal[]>([]);
  const [newDismissalDate, setNewDismissalDate] = useState("");
  const [newDismissalTime, setNewDismissalTime] = useState("");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [createdCount, setCreatedCount] = useState<number | null>(null);

  function addOffDate() {
    if (newOffDate && !offDates.includes(newOffDate)) {
      setOffDates((prev) => [...prev, newOffDate].sort());
    }
    setNewOffDate("");
  }

  function removeOffDate(date: string) {
    setOffDates((prev) => prev.filter((d) => d !== date));
  }

  function addEarlyDismissal() {
    if (newDismissalDate && newDismissalTime && !earlyDismissals.some((e) => e.date === newDismissalDate)) {
      setEarlyDismissals((prev) =>
        [...prev, { date: newDismissalDate, period5_end: newDismissalTime }].sort((a, b) =>
          a.date.localeCompare(b.date)
        )
      );
    }
    setNewDismissalDate("");
    setNewDismissalTime("");
  }

  function removeEarlyDismissal(date: string) {
    setEarlyDismissals((prev) => prev.filter((e) => e.date !== date));
  }

  function handleSubmit() {
    setError(null);
    setCreatedCount(null);
    startTransition(async () => {
      const result = await generateSchoolScheduleAction({
        start_date: startDate,
        end_date: endDate,
        start_day_number: startDayNumber,
        off_dates: offDates,
        early_dismissals: earlyDismissals,
      });
      if (result.error) {
        setError(result.error);
      } else {
        setCreatedCount(result.created_count ?? 0);
      }
    });
  }

  return (
    <section className="p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
        Add to Google Calendar
      </h2>

      {!googleConnected ? (
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Connect Google Calendar before adding your schedule.
          </p>
          <a
            href={googleLoginUrl}
            className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg transition-colors shrink-0"
          >
            Connect Google Calendar
          </a>
        </div>
      ) : (
        <>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
            Creates an event for every block in every school day between these dates, rotating
            through Day 1 - 6 starting from the day you pick below.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              First day of school
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className={inputClass}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              Last day of school
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className={inputClass}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              Rotation day on the first day
              <select
                value={startDayNumber}
                onChange={(e) => setStartDayNumber(e.target.value as DayNumber)}
                className={inputClass}
              >
                {DAY_NUMBERS.map((d) => (
                  <option key={d} value={d}>
                    Day {d}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mb-4">
            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400 mb-2">
              Days off (holidays, breaks — weekends are skipped automatically)
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="date"
                value={newOffDate}
                onChange={(e) => setNewOffDate(e.target.value)}
                className={inputClass}
              />
              <button
                type="button"
                onClick={addOffDate}
                className="shrink-0 bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-sm font-medium px-3 py-2 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-600 transition-colors"
              >
                Add
              </button>
            </div>
            {offDates.length > 0 && (
              <ul className="flex flex-wrap gap-2">
                {offDates.map((date) => (
                  <li
                    key={date}
                    className="flex items-center gap-1.5 text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-full px-2.5 py-1"
                  >
                    {date}
                    <button
                      type="button"
                      onClick={() => removeOffDate(date)}
                      aria-label={`Remove ${date}`}
                      className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mb-4">
            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400 mb-2">
              Early dismissal days (school still happens, but period 5 ends early)
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              <input
                type="date"
                value={newDismissalDate}
                onChange={(e) => setNewDismissalDate(e.target.value)}
                aria-label="Early dismissal date"
                className={inputClass}
              />
              <input
                type="time"
                value={newDismissalTime}
                onChange={(e) => setNewDismissalTime(e.target.value)}
                aria-label="Period 5 ends at"
                className={inputClass}
              />
              <button
                type="button"
                onClick={addEarlyDismissal}
                disabled={!newDismissalDate || !newDismissalTime}
                className="shrink-0 bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-sm font-medium px-3 py-2 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-600 disabled:opacity-50 transition-colors"
              >
                Add
              </button>
            </div>
            {earlyDismissals.length > 0 && (
              <ul className="flex flex-wrap gap-2">
                {earlyDismissals.map((e) => (
                  <li
                    key={e.date}
                    className="flex items-center gap-1.5 text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-full px-2.5 py-1"
                  >
                    {e.date} — ends {e.period5_end}
                    <button
                      type="button"
                      onClick={() => removeEarlyDismissal(e.date)}
                      aria-label={`Remove early dismissal on ${e.date}`}
                      className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={pending || !startDate || !endDate}
              className="w-full sm:w-auto bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {pending ? "Adding to calendar…" : "Add to Google Calendar"}
            </button>
            {createdCount !== null && !pending && (
              <span role="status" className="text-sm text-green-600 dark:text-green-400">
                Added {createdCount} event{createdCount === 1 ? "" : "s"} to your calendar.
              </span>
            )}
          </div>
        </>
      )}

      {error && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
    </section>
  );
}
