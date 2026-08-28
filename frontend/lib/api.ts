import { cookies } from "next/headers";

export const BASE = process.env.API_URL ?? "http://localhost:8000";
export const SESSION_COOKIE_NAME = "breadcrumbs_session";

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME);
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (session) {
    headers["Cookie"] = `${SESSION_COOKIE_NAME}=${session.value}`;
  }
  return fetch(`${BASE}${path}`, {
    cache: "no-store",
    ...options,
    headers,
  });
}

async function parseErrorDetail(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => ({}));
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

export type CurrentUser = {
  id: string;
  email: string | null;
  name: string | null;
  picture: string | null;
  google_connected: boolean;
};

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const res = await apiFetch("/auth/me");
  if (!res.ok) return null;
  const data = await res.json();
  return data.user ?? null;
}

export type Priority = "low" | "medium" | "high";

export type Task = {
  id: string;
  title: string;
  subject: string;
  estimated_minutes: number;
  actual_minutes: number[];
  status: "pending" | "scheduled" | "done" | "unschedulable";
  scheduled_blocks: { start: string; end: string }[];
  created_at: string;
  due_date: string | null;
  priority: Priority;
  estimated_minutes_used?: number;
  estimate_basis?: "user" | "historical";
  estimate_sample_size?: number;
  estimate_ratio?: number;
};

export async function fetchTasks(): Promise<Task[]> {
  const res = await apiFetch("/tasks");
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function createTask(data: {
  title: string;
  subject: string;
  estimated_minutes: number;
  due_date?: string | null;
  priority?: Priority;
}): Promise<Task> {
  const res = await apiFetch("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create task");
  return res.json();
}

export async function completeTask(
  id: string,
  actual_minutes?: number
): Promise<Task> {
  const res = await apiFetch(`/tasks/${id}/complete`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actual_minutes: actual_minutes ?? null }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to complete task"));
  }
  return res.json();
}

export async function deleteTask(id: string): Promise<void> {
  const res = await apiFetch(`/tasks/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete task");
}

export async function updateTask(
  id: string,
  data: Partial<{
    title: string;
    subject: string;
    estimated_minutes: number;
    due_date: string | null;
    priority: Priority;
  }>
): Promise<Task> {
  const res = await apiFetch(`/tasks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to update task"));
  }
  return res.json();
}

export async function rescheduleTask(id: string, start: string): Promise<Task> {
  const res = await apiFetch(`/tasks/${id}/reschedule`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to move task"));
  }
  return res.json();
}

export async function runScheduler(): Promise<unknown> {
  const res = await apiFetch("/schedule/run", { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "Scheduler failed");
  }
  return res.json();
}

export type TimeTrackingMode = "manual" | "automatic";

export type Settings = {
  day_start: string;
  day_end: string;
  timezone: string;
  max_continuous_minutes: number;
  max_subjects_per_day: number;
  lookahead_days: number;
  time_tracking_mode: TimeTrackingMode;
};

export async function fetchSettings(): Promise<Settings> {
  const res = await apiFetch("/settings");
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function updateSettings(
  data: Partial<Settings>
): Promise<Settings> {
  const res = await apiFetch("/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to update settings"));
  }
  return res.json();
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}

export async function disconnectGoogle(): Promise<void> {
  const res = await apiFetch("/account/disconnect-google", { method: "POST" });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to disconnect Google Calendar"));
  }
}

export async function deleteAccountData(): Promise<void> {
  const res = await apiFetch("/account/delete-data", { method: "POST" });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to delete your data"));
  }
}

export async function deleteAccount(): Promise<void> {
  const res = await apiFetch("/account", { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, "Failed to delete your account"));
  }
}
