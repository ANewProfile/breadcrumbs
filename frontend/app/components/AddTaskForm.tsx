import { createTaskAction } from "@/app/actions";

const inputClass =
  "bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500";

export function AddTaskForm() {
  return (
    <form
      action={createTaskAction}
      className="flex flex-col gap-3 mb-6 sm:mb-8 p-4 sm:p-5 border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900 shadow-sm"
    >
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide">
        Add Task
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="sr-only">Task title</span>
          <input
            name="title"
            type="text"
            required
            placeholder="Task title"
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="sr-only">Subject</span>
          <input
            name="subject"
            type="text"
            required
            placeholder="Subject (e.g. Math, CS, English)"
            className={inputClass}
          />
        </label>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Est. minutes
          <input
            name="estimated_minutes"
            type="number"
            required
            min="1"
            placeholder="30"
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Due date (optional)
          <input name="due_date" type="date" className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Priority
          <select name="priority" defaultValue="medium" className={inputClass}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
      </div>

      <button
        type="submit"
        className="w-full sm:w-auto sm:self-start bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-500 transition-colors"
      >
        Add task
      </button>
    </form>
  );
}
