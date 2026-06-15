const BASE = process.env.API_URL ?? "http://localhost:8000";

export type Task = {
  id: string;
  title: string;
  subject: string;
  estimated_minutes: number;
  actual_minutes: number[];
  status: "pending" | "scheduled" | "done";
  scheduled_blocks: { start: string; end: string }[];
  created_at: string;
};

export async function fetchTasks(): Promise<Task[]> {
  const res = await fetch(`${BASE}/tasks`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function createTask(data: {
  title: string;
  subject: string;
  estimated_minutes: number;
}): Promise<Task> {
  const res = await fetch(`${BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create task");
  return res.json();
}

export async function completeTask(
  id: string,
  actual_minutes: number
): Promise<Task> {
  const res = await fetch(`${BASE}/tasks/${id}/complete`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actual_minutes }),
  });
  if (!res.ok) throw new Error("Failed to complete task");
  return res.json();
}

export async function deleteTask(id: string): Promise<void> {
  const res = await fetch(`${BASE}/tasks/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete task");
}

export async function runScheduler(): Promise<unknown> {
  const res = await fetch(`${BASE}/schedule/run`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "Scheduler failed");
  }
  return res.json();
}
