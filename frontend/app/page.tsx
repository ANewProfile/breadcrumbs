import { fetchTasks } from "@/lib/api";
import { AddTaskForm } from "./components/AddTaskForm";
import { RunSchedulerBtn } from "./components/RunSchedulerBtn";
import { TaskCard } from "./components/TaskCard";

export default async function Home() {
  const tasks = await fetchTasks();
  const pending = tasks.filter((t) => t.status === "pending");
  const scheduled = tasks.filter((t) => t.status === "scheduled");
  const unschedulable = tasks.filter((t) => t.status === "unschedulable");

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold text-zinc-900 mb-1">Breadcrumbs</h1>
      <p className="text-sm text-zinc-500 mb-8">Your study scheduler</p>

      <AddTaskForm />
      <RunSchedulerBtn />

      {scheduled.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide mb-3">
            Scheduled
          </h2>
          <ul className="space-y-2">
            {scheduled.map((t) => (
              <TaskCard key={t.id} task={t} />
            ))}
          </ul>
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
