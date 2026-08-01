import { createTaskAction } from "@/app/actions";

export function AddTaskForm() {
  return (
    <form
      action={createTaskAction}
      className="flex flex-col gap-3 mb-8 p-4 border border-zinc-200 rounded-xl bg-zinc-50"
    >
      <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide">
        Add Task
      </h2>
      <input
        name="title"
        type="text"
        required
        placeholder="Task title"
        className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
      />
      <input
        name="subject"
        type="text"
        required
        placeholder="Subject (e.g. Math, CS, English)"
        className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
      />
      <div className="flex items-center gap-2">
        <input
          name="estimated_minutes"
          type="number"
          required
          min="1"
          placeholder="Est. minutes"
          className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-zinc-400"
        />
        <span className="text-sm text-zinc-500">minutes</span>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex flex-col gap-1 text-xs text-zinc-500">
          Due date (optional)
          <input
            name="due_date"
            type="date"
            className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500">
          Priority
          <select
            name="priority"
            defaultValue="medium"
            className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
      </div>
      <button
        type="submit"
        className="self-start bg-zinc-900 text-white text-sm px-4 py-2 rounded-lg hover:bg-zinc-700 transition-colors"
      >
        Add
      </button>
    </form>
  );
}
