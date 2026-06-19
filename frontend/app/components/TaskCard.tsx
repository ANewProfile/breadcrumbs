"use client";

import { useState } from "react";
import type { Task } from "@/lib/api";
import { completeTaskAction, deleteTaskAction } from "@/app/actions";

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

const SUBJECT_COLORS: Record<string, string> = {
  math: "bg-purple-100 text-purple-800",
  cs: "bg-blue-100 text-blue-800",
  english: "bg-green-100 text-green-800",
  science: "bg-yellow-100 text-yellow-800",
  history: "bg-orange-100 text-orange-800",
};

function subjectColor(subject: string) {
  return (
    SUBJECT_COLORS[subject.toLowerCase()] ?? "bg-zinc-100 text-zinc-700"
  );
}

export function TaskCard({ task }: { task: Task }) {
  const [completing, setCompleting] = useState(false);
  const block = task.scheduled_blocks[0];

  return (
    <li className="flex flex-col gap-2 p-4 border border-zinc-200 rounded-xl bg-white">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-zinc-900 truncate">{task.title}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${subjectColor(task.subject)}`}
            >
              {task.subject}
            </span>
            <span className="text-xs text-zinc-500">
              ~{task.estimated_minutes} min
            </span>
            {block && (
              <span className="text-xs text-blue-600 font-medium">
                {formatTime(block.start)} – {formatTime(block.end)}
              </span>
            )}
          </div>
        </div>

        <div className="flex gap-2 shrink-0">
          {task.status !== "unschedulable" && (
            <button
              onClick={() => setCompleting((v) => !v)}
              className="text-xs bg-green-100 text-green-800 px-3 py-1 rounded-lg hover:bg-green-200 transition-colors"
            >
              Complete
            </button>
          )}
          <form action={deleteTaskAction}>
            <input type="hidden" name="id" value={task.id} />
            <button
              type="submit"
              className="text-xs bg-zinc-100 text-zinc-600 px-3 py-1 rounded-lg hover:bg-zinc-200 transition-colors"
            >
              Delete
            </button>
          </form>
        </div>
      </div>

      {completing && (
        <form
          action={completeTaskAction}
          className="flex items-center gap-2 mt-1 pt-2 border-t border-zinc-100"
        >
          <input type="hidden" name="id" value={task.id} />
          <input
            name="actual_minutes"
            type="number"
            required
            min="1"
            placeholder="Actual minutes"
            className="border border-zinc-300 rounded-lg px-3 py-1.5 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-green-400"
            autoFocus
          />
          <button
            type="submit"
            className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-500 transition-colors"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setCompleting(false)}
            className="text-sm text-zinc-500 hover:text-zinc-700"
          >
            Cancel
          </button>
        </form>
      )}
    </li>
  );
}
