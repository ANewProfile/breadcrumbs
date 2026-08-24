"use client";

import { useState, useTransition } from "react";
import { updateSchoolScheduleAction } from "@/app/actions";
import type { SchoolSchedule, BellTime, BellTimes, BlockLetter, DayNumber, DaySchedule } from "@/lib/api";

const BLOCK_LETTERS: BlockLetter[] = ["A", "B", "C", "D", "E", "F", "G", "T"];
const DAY_NUMBERS: DayNumber[] = ["1", "2", "3", "4", "5", "6"];
const DEFAULT_Z_TIME: BellTime = { start: "07:15", end: "07:55" };

// Schedules saved before the early-dismissal feature existed won't have
// period5_end at all (undefined, not null) — normalize it here so a controlled
// <input> never receives undefined, regardless of what the API returns.
function normalizeDaySchedules(
  raw: Record<DayNumber, DaySchedule>
): Record<DayNumber, DaySchedule> {
  const normalized = {} as Record<DayNumber, DaySchedule>;
  for (const day of DAY_NUMBERS) {
    normalized[day] = { ...raw[day], period5_end: raw[day].period5_end ?? null };
  }
  return normalized;
}

const inputClass =
  "bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500";

const BELL_TIME_FIELDS: { key: "p1" | "p2" | "p4" | "p5"; label: string }[] = [
  { key: "p1", label: "Period 1" },
  { key: "p2", label: "Period 2" },
  { key: "p4", label: "Period 4" },
  { key: "p5", label: "Period 5" },
];

function TimeField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: BellTime;
  onChange: (field: "start" | "end", newValue: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2 items-end">
      <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400 col-span-2">
        {label}
      </label>
      <input
        type="time"
        value={value.start}
        onChange={(e) => onChange("start", e.target.value)}
        className={inputClass}
        aria-label={`${label} start`}
      />
      <input
        type="time"
        value={value.end}
        onChange={(e) => onChange("end", e.target.value)}
        className={inputClass}
        aria-label={`${label} end`}
      />
    </div>
  );
}

function BlockSelect({
  value,
  courses,
  onChange,
}: {
  value: BlockLetter | null;
  courses: Partial<Record<BlockLetter, string>>;
  onChange: (value: BlockLetter | null) => void;
}) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value === "" ? null : (e.target.value as BlockLetter))}
      className={inputClass}
    >
      <option value="">None</option>
      {BLOCK_LETTERS.map((letter) => (
        <option key={letter} value={letter}>
          {courses[letter] ? `${letter} — ${courses[letter]}` : letter}
        </option>
      ))}
    </select>
  );
}

export function SchoolScheduleForm({ schedule }: { schedule: SchoolSchedule }) {
  const [bellTimes, setBellTimes] = useState<BellTimes>(schedule.bell_times);
  const [zEnabled, setZEnabled] = useState(schedule.bell_times.z !== null);
  const [courses, setCourses] = useState<Partial<Record<BlockLetter, string>>>(schedule.courses);
  const [daySchedules, setDaySchedules] = useState(() =>
    normalizeDaySchedules(schedule.day_schedules)
  );
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function updateBellTime(key: "z" | "p1" | "p2" | "p4" | "p5", field: "start" | "end", value: string) {
    setBellTimes((prev) => ({
      ...prev,
      [key]: { ...(prev[key] as BellTime), [field]: value },
    }));
  }

  function updateWaveTime(
    wave: "wave1" | "wave2",
    part: "lunch" | "period3",
    field: "start" | "end",
    value: string
  ) {
    setBellTimes((prev) => ({
      ...prev,
      [wave]: { ...prev[wave], [part]: { ...prev[wave][part], [field]: value } },
    }));
  }

  function updateDayZ(day: DayNumber, value: BlockLetter | null) {
    setDaySchedules((prev) => ({ ...prev, [day]: { ...prev[day], z: value } }));
  }

  function updateDayPeriod(day: DayNumber, index: number, value: BlockLetter | null) {
    setDaySchedules((prev) => {
      const periods = [...prev[day].periods];
      periods[index] = value;
      return { ...prev, [day]: { ...prev[day], periods } };
    });
  }

  function updateDayLunchWave(day: DayNumber, wave: 1 | 2) {
    setDaySchedules((prev) => ({ ...prev, [day]: { ...prev[day], lunch_wave: wave } }));
  }

  function updateDayPeriod5End(day: DayNumber, value: string) {
    setDaySchedules((prev) => ({
      ...prev,
      [day]: { ...prev[day], period5_end: value === "" ? null : value },
    }));
  }

  function handleSave() {
    setError(null);
    setSaved(false);
    startTransition(async () => {
      const cleanedCourses = Object.fromEntries(
        Object.entries(courses).filter(([, name]) => name && name.trim() !== "")
      );
      const result = await updateSchoolScheduleAction({
        bell_times: { ...bellTimes, z: zEnabled ? bellTimes.z ?? DEFAULT_Z_TIME : null },
        courses: cleanedCourses,
        day_schedules: daySchedules,
      });
      if (result.error) {
        setError(result.error);
      } else {
        setSaved(true);
      }
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
          Bell times
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
          The clock times for each period slot — the same every rotation day. Lunch wave 1 and
          wave 2 run on independent times around 3rd period, so set both separately below.
        </p>

        <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300 mb-4">
          <input
            type="checkbox"
            checked={zEnabled}
            onChange={(e) => setZEnabled(e.target.checked)}
            className="rounded border-zinc-300 dark:border-zinc-600"
          />
          I have a Z block (early morning period)
        </label>

        {zEnabled && (
          <div className="grid grid-cols-2 gap-3 mb-4">
            <TimeField
              label="Z block"
              value={bellTimes.z ?? DEFAULT_Z_TIME}
              onChange={(field, value) => updateBellTime("z", field, value)}
            />
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          {BELL_TIME_FIELDS.filter((f) => f.key === "p1" || f.key === "p2").map(({ key, label }) => (
            <TimeField
              key={key}
              label={label}
              value={bellTimes[key]}
              onChange={(field, value) => updateBellTime(key, field, value)}
            />
          ))}
        </div>

        <div className="mb-4">
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-2">
            3rd period &amp; lunch — independent times per wave
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-3 bg-white dark:bg-zinc-950">
              <h4 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
                Lunch wave 1 (lunch, then 3rd period)
              </h4>
              <div className="flex flex-col gap-2">
                <TimeField
                  label="Lunch"
                  value={bellTimes.wave1.lunch}
                  onChange={(field, value) => updateWaveTime("wave1", "lunch", field, value)}
                />
                <TimeField
                  label="3rd period"
                  value={bellTimes.wave1.period3}
                  onChange={(field, value) => updateWaveTime("wave1", "period3", field, value)}
                />
              </div>
            </div>
            <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-3 bg-white dark:bg-zinc-950">
              <h4 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
                Lunch wave 2 (3rd period, then lunch)
              </h4>
              <div className="flex flex-col gap-2">
                <TimeField
                  label="3rd period"
                  value={bellTimes.wave2.period3}
                  onChange={(field, value) => updateWaveTime("wave2", "period3", field, value)}
                />
                <TimeField
                  label="Lunch"
                  value={bellTimes.wave2.lunch}
                  onChange={(field, value) => updateWaveTime("wave2", "lunch", field, value)}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {BELL_TIME_FIELDS.filter((f) => f.key === "p4" || f.key === "p5").map(({ key, label }) => (
            <TimeField
              key={key}
              label={label}
              value={bellTimes[key]}
              onChange={(field, value) => updateBellTime(key, field, value)}
            />
          ))}
        </div>
      </section>

      <section className="p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
          Course names
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
          Optional — label each block so calendar events show the course name instead of just the
          letter.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {BLOCK_LETTERS.map((letter) => (
            <label key={letter} className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              {letter} block
              <input
                type="text"
                value={courses[letter] ?? ""}
                onChange={(e) => setCourses((prev) => ({ ...prev, [letter]: e.target.value }))}
                placeholder={`${letter} Block`}
                className={inputClass}
              />
            </label>
          ))}
        </div>
      </section>

      <section className="p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
          Day rotation
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
          Which block meets in each period slot, for each of the 6 rotating days.
        </p>
        <div className="flex flex-col gap-4">
          {DAY_NUMBERS.map((day) => {
            const daySchedule = daySchedules[day];
            return (
              <div
                key={day}
                className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-3 bg-white dark:bg-zinc-950"
              >
                <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mb-3">
                  Day {day}
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mb-3">
                  <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
                    Z block
                    <BlockSelect
                      value={daySchedule.z}
                      courses={courses}
                      onChange={(v) => updateDayZ(day, v)}
                    />
                  </label>
                  {daySchedule.periods.map((period, i) => (
                    <label
                      key={i}
                      className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400"
                    >
                      Period {i + 1}
                      <BlockSelect
                        value={period}
                        courses={courses}
                        onChange={(v) => updateDayPeriod(day, i, v)}
                      />
                    </label>
                  ))}
                </div>
                <fieldset className="flex items-center gap-4">
                  <legend className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">
                    Lunch wave
                  </legend>
                  {([1, 2] as const).map((wave) => (
                    <label
                      key={wave}
                      className="flex items-center gap-1.5 text-sm text-zinc-700 dark:text-zinc-300"
                    >
                      <input
                        type="radio"
                        name={`lunch-wave-${day}`}
                        checked={daySchedule.lunch_wave === wave}
                        onChange={() => updateDayLunchWave(day, wave)}
                        className="border-zinc-300 dark:border-zinc-600"
                      />
                      Lunch {wave} ({wave === 1 ? "before" : "after"} 3rd period)
                    </label>
                  ))}
                </fieldset>

                <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300 mt-3">
                  <input
                    type="checkbox"
                    checked={daySchedule.period5_end !== null}
                    onChange={(e) =>
                      updateDayPeriod5End(day, e.target.checked ? bellTimes.p5.end : "")
                    }
                    className="rounded border-zinc-300 dark:border-zinc-600"
                  />
                  Early dismissal on this day
                </label>
                {daySchedule.period5_end !== null && (
                  <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400 mt-2 max-w-[10rem]">
                    Period 5 ends at
                    <input
                      type="time"
                      value={daySchedule.period5_end}
                      onChange={(e) => updateDayPeriod5End(day, e.target.value)}
                      className={inputClass}
                    />
                  </label>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={pending}
          className="w-full sm:w-auto bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
        >
          {pending ? "Saving…" : "Save schedule"}
        </button>
        {saved && !pending && (
          <span role="status" className="text-sm text-green-600 dark:text-green-400">
            Saved.
          </span>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
