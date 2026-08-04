import { fetchTasks, fetchSettings, fetchCurrentUser, BASE, type Task } from "@/lib/api";
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
  const user = await fetchCurrentUser();

  if (!user) {
    return (
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        <div className="flex flex-col items-center text-center mt-12 sm:mt-20 px-4">
          <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Your tasks
          </h1>
          <p className="text-sm sm:text-base text-zinc-500 dark:text-zinc-400 mt-2 max-w-sm">
            Sign in with Google to connect your calendar and start scheduling.
          </p>
          <a
            href={`${BASE}/auth/google/login`}
            className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 rounded-lg transition-colors"
          >
            Sign in with Google
          </a>
        </div>
      </main>
    );
  }

  const [tasks, settings] = await Promise.all([fetchTasks(), fetchSettings()]);
  const timeTrackingMode = settings.time_tracking_mode;
  const pending = tasks.filter((t) => t.status === "pending");
  const scheduled = tasks.filter((t) => t.status === "scheduled");
  const unschedulable = tasks.filter((t) => t.status === "unschedulable");
  const scheduledByDay = groupScheduledByDay(scheduled);

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
          Your tasks
        </h1>
        <p className="text-sm sm:text-base text-zinc-500 dark:text-zinc-400 mt-1">
          Add a task, then run the scheduler to fit it into your free time.
        </p>
      </div>

      <AddTaskForm />
      <RunSchedulerBtn />

      {scheduledByDay.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
            Scheduled
          </h2>
          <div className="space-y-5">
            {scheduledByDay.map((day) => (
              <div key={day.date}>
                <h3 className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wide mb-2">
                  {day.label}
                </h3>
                <ul className="space-y-2">
                  {day.tasks.map((t) => (
                    <TaskCard key={t.id} task={t} timeTrackingMode={timeTrackingMode} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {pending.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-3">
            Pending
          </h2>
          <ul className="space-y-2">
            {pending.map((t) => (
              <TaskCard key={t.id} task={t} timeTrackingMode={timeTrackingMode} />
            ))}
          </ul>
        </section>
      )}

      {unschedulable.length > 0 && (
        <section className="mb-8">
          <div className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950 px-4 py-3 mb-3">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
              {unschedulable.length} task{unschedulable.length > 1 ? "s" : ""} couldn't be scheduled — no free block large enough.
            </p>
          </div>
          <ul className="space-y-2">
            {unschedulable.map((t) => (
              <TaskCard key={t.id} task={t} timeTrackingMode={timeTrackingMode} />
            ))}
          </ul>
        </section>
      )}

      {tasks.length === 0 && (
        <div className="flex flex-col items-center text-center mt-12 sm:mt-16 px-4">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            className="w-10 h-10 text-zinc-300 dark:text-zinc-700 mb-3"
            aria-hidden="true"
          >
            <path
              d="M5 13l4 4L19 7"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.4"
            />
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
          </svg>
          <p className="text-zinc-500 dark:text-zinc-400 text-sm font-medium">
            No tasks yet
          </p>
          <p className="text-zinc-400 dark:text-zinc-500 text-sm mt-1">
            Add one above to get started.
          </p>
        </div>
      )}
    </main>
  );
}
