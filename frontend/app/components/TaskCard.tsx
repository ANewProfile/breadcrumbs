"use client";

import { useState, useTransition, useEffect } from "react";
import type { Task, TimeTrackingMode } from "@/lib/api";
import {
  completeTaskAction,
  deleteTaskAction,
  updateTaskAction,
  rescheduleTaskAction,
} from "@/app/actions";

function toDatetimeLocalValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDueDate(dueDate: string) {
  const due = new Date(`${dueDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((due.getTime() - today.getTime()) / 86400000);

  const label = due.toLocaleDateString([], { month: "short", day: "numeric" });
  if (days < 0) return { text: `Overdue (${label})`, urgent: true };
  if (days === 0) return { text: "Due today", urgent: true };
  if (days === 1) return { text: "Due tomorrow", urgent: true };
  return { text: `Due ${label}`, urgent: false };
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

const SUBJECT_COLORS: Record<string, string> = {
  math: "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300",
  cs: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  english: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  science: "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
  history: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
};

function subjectColor(subject: string) {
  return (
    SUBJECT_COLORS[subject.toLowerCase()] ??
    "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
  );
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  medium: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  low: "bg-zinc-50 text-zinc-400 dark:bg-zinc-900 dark:text-zinc-500",
};

type TimerState = {
  accumulatedMs: number;
  runningSince: number | null;
};

function timerStorageKey(taskId: string) {
  return `breadcrumbs_timer_${taskId}`;
}

function loadTimerState(taskId: string): TimerState {
  if (typeof window === "undefined") return { accumulatedMs: 0, runningSince: null };
  try {
    const raw = window.localStorage.getItem(timerStorageKey(taskId));
    if (!raw) return { accumulatedMs: 0, runningSince: null };
    const parsed = JSON.parse(raw);
    return {
      accumulatedMs: typeof parsed.accumulatedMs === "number" ? parsed.accumulatedMs : 0,
      runningSince: typeof parsed.runningSince === "number" ? parsed.runningSince : null,
    };
  } catch {
    return { accumulatedMs: 0, runningSince: null };
  }
}

export function TaskCard({
  task,
  timeTrackingMode,
}: {
  task: Task;
  timeTrackingMode: TimeTrackingMode;
}) {
  const [completing, setCompleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [moving, setMoving] = useState(false);
  const [editPending, startEditTransition] = useTransition();
  const [movePending, startMoveTransition] = useTransition();
  const [completePending, startCompleteTransition] = useTransition();
  const [editError, setEditError] = useState<string | null>(null);
  const [moveError, setMoveError] = useState<string | null>(null);
  const [completeError, setCompleteError] = useState<string | null>(null);
  const [timerAccumulatedMs, setTimerAccumulatedMs] = useState(0);
  const [timerRunningSince, setTimerRunningSince] = useState<number | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const block = task.scheduled_blocks[0];

  // Restore any in-progress timer for this task (e.g. after a page reload).
  useEffect(() => {
    const restored = loadTimerState(task.id);
    setTimerAccumulatedMs(restored.accumulatedMs);
    setTimerRunningSince(restored.runningSince);
  }, [task.id]);

  // Persist timer state so a reload mid-task doesn't lose elapsed time.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (timerAccumulatedMs === 0 && timerRunningSince === null) {
      window.localStorage.removeItem(timerStorageKey(task.id));
    } else {
      window.localStorage.setItem(
        timerStorageKey(task.id),
        JSON.stringify({ accumulatedMs: timerAccumulatedMs, runningSince: timerRunningSince })
      );
    }
  }, [task.id, timerAccumulatedMs, timerRunningSince]);

  // Tick the display once a second while the timer is running.
  useEffect(() => {
    if (timerRunningSince === null) return;
    setNowMs(Date.now());
    const interval = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [timerRunningSince]);

  const elapsedMs =
    timerAccumulatedMs + (timerRunningSince !== null ? nowMs - timerRunningSince : 0);
  const elapsedMinutes = Math.round(elapsedMs / 60000);

  function clearTimer() {
    setTimerAccumulatedMs(0);
    setTimerRunningSince(null);
  }

  function handleTimerStart() {
    setTimerRunningSince(Date.now());
  }

  function handleTimerPause() {
    setTimerAccumulatedMs((prev) =>
      prev + (timerRunningSince !== null ? Date.now() - timerRunningSince : 0)
    );
    setTimerRunningSince(null);
  }

  function handleEditSubmit(formData: FormData) {
    setEditError(null);
    startEditTransition(async () => {
      const result = await updateTaskAction(task.id, formData);
      if (result.error) {
        setEditError(result.error);
      } else {
        setEditing(false);
      }
    });
  }

  function handleMoveSubmit(formData: FormData) {
    setMoveError(null);
    const raw = formData.get("start") as string;
    const iso = new Date(raw).toISOString();
    startMoveTransition(async () => {
      const result = await rescheduleTaskAction(task.id, iso);
      if (result.error) {
        setMoveError(result.error);
      } else {
        setMoving(false);
      }
    });
  }

  function handleCompleteSubmit(formData: FormData) {
    setCompleteError(null);
    const intent = formData.get("intent") as string;
    const fd = new FormData();
    fd.set("id", task.id);
    if (intent === "save") {
      const minutes =
        timeTrackingMode === "automatic"
          ? elapsedMinutes
          : parseInt(formData.get("actual_minutes") as string, 10);
      if (!Number.isNaN(minutes) && minutes > 0) {
        fd.set("actual_minutes", String(minutes));
      }
    }
    // intent === "unknown" -> actual_minutes intentionally omitted
    startCompleteTransition(async () => {
      const result = await completeTaskAction(fd);
      if (result.error) {
        setCompleteError(result.error);
      } else {
        setCompleting(false);
        clearTimer();
      }
    });
  }

  return (
    <li className="flex flex-col gap-2 p-4 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-zinc-900 dark:text-zinc-100 truncate">{task.title}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${subjectColor(task.subject)}`}
            >
              {task.subject}
            </span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              ~{task.estimated_minutes} min
            </span>
            {task.priority !== "medium" && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[task.priority]}`}
              >
                {task.priority}
              </span>
            )}
            {task.due_date && (
              <span
                className={`text-xs font-medium ${
                  formatDueDate(task.due_date).urgent
                    ? "text-red-600 dark:text-red-400"
                    : "text-zinc-500 dark:text-zinc-400"
                }`}
              >
                {formatDueDate(task.due_date).text}
              </span>
            )}
            {block && (
              <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                {formatTime(block.start)} – {formatTime(block.end)}
              </span>
            )}
          </div>

          {task.estimate_basis === "historical" &&
            task.estimated_minutes_used !== undefined && (
              <p className="text-xs text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950 rounded-lg px-2 py-1 mt-1.5 inline-block">
                Scheduled {task.estimated_minutes_used} min — your last{" "}
                {task.estimate_sample_size} {task.subject} session
                {task.estimate_sample_size === 1 ? "" : "s"}{" "}
                {task.estimate_ratio !== undefined &&
                  `ran ~${task.estimate_ratio}x your predicted time (weighted toward recent). `}
                You estimated {task.estimated_minutes}.
              </p>
            )}
        </div>

        <div className="flex gap-2 shrink-0 flex-wrap sm:justify-end">
          {task.status !== "unschedulable" && (
            <button
              onClick={() => setCompleting((v) => !v)}
              className="text-xs bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300 px-3 py-1.5 rounded-lg hover:bg-green-200 dark:hover:bg-green-900 focus:outline-none focus:ring-2 focus:ring-green-400 transition-colors"
            >
              Complete
            </button>
          )}
          <button
            onClick={() => setMoving((v) => !v)}
            className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 px-3 py-1.5 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-colors"
          >
            Move
          </button>
          <button
            onClick={() => setEditing((v) => !v)}
            className="text-xs bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 px-3 py-1.5 rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-zinc-400 transition-colors"
          >
            Edit
          </button>
          <form action={deleteTaskAction}>
            <input type="hidden" name="id" value={task.id} />
            <button
              type="submit"
              className="text-xs bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 px-3 py-1.5 rounded-lg hover:bg-red-100 hover:text-red-700 dark:hover:bg-red-950 dark:hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-400 transition-colors"
            >
              Delete
            </button>
          </form>
        </div>
      </div>

      {completing && (
        <div className="mt-1 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          {timeTrackingMode === "manual" ? (
            <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950 rounded-lg px-2 py-1 mb-2 inline-block">
              ⏱ Don&apos;t forget to record how long this actually took — it
              helps future estimates get smarter.
            </p>
          ) : (
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-lg text-zinc-800 dark:text-zinc-200 tabular-nums">
                {formatElapsed(elapsedMs)}
              </span>
              <button
                type="button"
                onClick={timerRunningSince !== null ? handleTimerPause : handleTimerStart}
                className={`text-sm px-3 py-1.5 rounded-lg transition-colors ${
                  timerRunningSince !== null
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-900"
                    : "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900"
                }`}
              >
                {timerRunningSince !== null ? "Pause" : "Start"}
              </button>
            </div>
          )}

          <form action={handleCompleteSubmit} className="flex items-center gap-2 flex-wrap">
            {timeTrackingMode === "manual" && (
              <input
                name="actual_minutes"
                type="number"
                required
                min="1"
                placeholder="Actual minutes"
                className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-green-400"
                autoFocus
              />
            )}
            <button
              type="submit"
              name="intent"
              value="save"
              disabled={
                completePending ||
                (timeTrackingMode === "automatic" && elapsedMinutes <= 0)
              }
              className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-500 disabled:opacity-50 transition-colors"
            >
              {completePending
                ? "Saving…"
                : timeTrackingMode === "automatic"
                  ? "Complete"
                  : "Save"}
            </button>
            <button
              type="submit"
              name="intent"
              value="unknown"
              formNoValidate
              disabled={completePending}
              className="text-sm bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 px-3 py-1.5 rounded-lg hover:bg-zinc-200 dark:hover:bg-zinc-700 disabled:opacity-50 transition-colors"
            >
              I don&apos;t know how long it took
            </button>
            <button
              type="button"
              onClick={() => {
                setCompleting(false);
                setCompleteError(null);
              }}
              className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              Cancel
            </button>
          </form>
          {completeError && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{completeError}</p>
          )}
        </div>
      )}

      {moving && (
        <div className="mt-1 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          <form action={handleMoveSubmit} className="flex items-center gap-2 flex-wrap">
            <input
              name="start"
              type="datetime-local"
              required
              defaultValue={block ? toDatetimeLocalValue(block.start) : undefined}
              className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              autoFocus
            />
            <button
              type="submit"
              disabled={movePending}
              className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {movePending ? "Moving…" : "Move here"}
            </button>
            <button
              type="button"
              onClick={() => {
                setMoving(false);
                setMoveError(null);
              }}
              className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              Cancel
            </button>
          </form>
          {moveError && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{moveError}</p>}
        </div>
      )}

      {editing && (
        <div className="mt-1 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          <form action={handleEditSubmit} className="flex flex-col gap-2">
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                name="title"
                type="text"
                required
                defaultValue={task.title}
                placeholder="Task title"
                className="flex-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
              />
              <input
                name="subject"
                type="text"
                required
                defaultValue={task.subject}
                placeholder="Subject"
                className="flex-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
              />
            </div>
            <div className="flex flex-wrap gap-2 items-center">
              <input
                name="estimated_minutes"
                type="number"
                required
                min="1"
                defaultValue={task.estimated_minutes}
                className="w-28 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
              />
              <span className="text-sm text-zinc-500 dark:text-zinc-400">min</span>
              <input
                name="due_date"
                type="date"
                defaultValue={task.due_date ?? ""}
                className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
              />
              <select
                name="priority"
                defaultValue={task.priority}
                className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={editPending}
                className="self-start text-sm bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 px-3 py-1.5 rounded-lg hover:bg-zinc-700 dark:hover:bg-zinc-300 disabled:opacity-50 transition-colors"
              >
                {editPending ? "Saving…" : "Save changes"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setEditError(null);
                }}
                className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              >
                Cancel
              </button>
            </div>
          </form>
          {editError && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{editError}</p>}
        </div>
      )}
    </li>
  );
}
