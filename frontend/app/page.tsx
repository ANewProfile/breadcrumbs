import Link from "next/link";
import { fetchTasks, type Task } from "@/lib/api";
import { AddTaskForm } from "./components/AddTaskForm";
import { RunSchedulerBtn } from "./components/RunSchedulerBtn";
import { TaskCard } from "./components/TaskCard";

function dayLabel(dateStr: string): string {
  const date = new Date(`${dateStr}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((date.getTime() - today.getTime()) / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  return date.toLocaleDateString([], {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function groupScheduledByDay(tasks: Task[]) {
  const groups = new Map<string, Task[]>();
  for (const t of tasks) {
    const block = t.scheduled_blocks[0];
    if (!block) continue;
    const dateKey = block.start.slice(0, 10);
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey)!.push(t);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, dayTasks]) => ({
      date,
      label: dayLabel(date),
      tasks: [...dayTasks].sort((a, b) =>
        a.scheduled_blocks[0].start.localeCompare(b.scheduled_blocks[0].start)
      ),
    }));
}

export default async function Home() {
  const tasks = await fetchTasks();
  const pending = tasks.filter((t) => t.status === "pending");
  const scheduled = tasks.filter((t) => t.status === "scheduled");
  const unschedulable = tasks.filter((t) => t.status === "unschedulable");
  const scheduledByDay = groupScheduledByDay(scheduled);

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-start justify-between mb-1">
        <h1 className="text-3xl font-bold text-zinc-900">Breadcrumbs</h1>
        <Link
          href="/settings"
          className="text-sm text-zinc-500 hover:text-zinc-700 mt-2"
        >
          Settings
        </Link>
      </div>
      <p className="text-sm text-zinc-500 mb-8">Your study scheduler</p>

      <AddTaskForm />
      <RunSchedulerBtn />

      {scheduledByDay.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-3">
            Scheduled
          </h2>
          <div className="space-y-5">
            {scheduledByDay.map((day) => (
              <div key={day.date}>
                <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
                  {day.label}
                </h3>
                <ul className="space-y-2">
                  {day.tasks.map((t) => (
                    <TaskCard key={t.id} task={t} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {pending.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-3">
            Pending
          </h2>
          <ul className="space-y-2">
            {pending.map((t) => (
              <TaskCard key={t.id} task={t} />
            ))}
          </ul>
        </section>
      )}

      {unschedulable.length > 0 && (
        <section className="mb-8">
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 mb-3">
            <p className="text-sm font-medium text-amber-800">
              {unschedulable.length} task{unschedulable.length > 1 ? "s" : ""} couldn't be scheduled — no free block large enough.
            </p>
          </div>
          <ul className="space-y-2">
            {unschedulable.map((t) => (
              <TaskCard key={t.id} task={t} />
            ))}
          </ul>
        </section>
      )}

      {tasks.length === 0 && (
        <p className="text-zinc-400 text-sm text-center mt-16">
          No tasks yet — add one above.
        </p>
      )}
    </main>
  );
}
