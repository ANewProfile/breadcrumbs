"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import {
  createTask,
  completeTask,
  deleteTask,
  updateTask,
  rescheduleTask,
  runScheduler,
  rescheduleMissed,
  updateSettings,
  logout,
  disconnectGoogle,
  deleteAccountData,
  deleteAccount,
  createNoGoZone,
  deleteNoGoZone,
  SESSION_COOKIE_NAME,
  type Priority,
  type Settings,
  type TimeTrackingMode,
} from "@/lib/api";

export async function createTaskAction(
  formData: FormData
): Promise<{ error?: string }> {
  const title = formData.get("title") as string;
  const subject = formData.get("subject") as string;
  const estimated_minutes = parseInt(
    formData.get("estimated_minutes") as string,
    10
  );
  const due_date = (formData.get("due_date") as string) || null;
  const priority = (formData.get("priority") as Priority) || "medium";
  try {
    await createTask({ title, subject, estimated_minutes, due_date, priority });
  } catch (e) {
    return { error: (e as Error).message };
  }
  revalidatePath("/");
  return {};
}

export async function completeTaskAction(
  formData: FormData
): Promise<{ error?: string }> {
  const id = formData.get("id") as string;
  const rawMinutes = formData.get("actual_minutes") as string | null;
  const actual_minutes =
    rawMinutes && rawMinutes.length > 0 ? parseInt(rawMinutes, 10) : undefined;
  try {
    await completeTask(id, actual_minutes);
    revalidatePath("/");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function deleteTaskAction(formData: FormData) {
  const id = formData.get("id") as string;
  await deleteTask(id);
  revalidatePath("/");
}

export async function updateTaskAction(
  id: string,
  formData: FormData
): Promise<{ error?: string }> {
  const title = formData.get("title") as string;
  const subject = formData.get("subject") as string;
  const estimated_minutes = parseInt(
    formData.get("estimated_minutes") as string,
    10
  );
  const due_date = (formData.get("due_date") as string) || null;
  const priority = formData.get("priority") as Priority;
  try {
    await updateTask(id, { title, subject, estimated_minutes, due_date, priority });
    revalidatePath("/");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function rescheduleTaskAction(
  id: string,
  startIso: string
): Promise<{ error?: string }> {
  try {
    await rescheduleTask(id, startIso);
    revalidatePath("/");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function runSchedulerAction(): Promise<{ error?: string }> {
  try {
    await runScheduler();
    revalidatePath("/");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function rescheduleMissedAction(): Promise<{ error?: string }> {
  try {
    await rescheduleMissed();
    revalidatePath("/");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function updateSettingsAction(
  formData: FormData
): Promise<{ error?: string }> {
  const data: Partial<Settings> = {
    day_start: formData.get("day_start") as string,
    day_end: formData.get("day_end") as string,
    timezone: formData.get("timezone") as string,
    max_continuous_minutes: parseInt(
      formData.get("max_continuous_minutes") as string,
      10
    ),
    max_subjects_per_day: parseInt(
      formData.get("max_subjects_per_day") as string,
      10
    ),
    lookahead_days: parseInt(formData.get("lookahead_days") as string, 10),
    time_tracking_mode: formData.get("time_tracking_mode") as TimeTrackingMode,
    break_between_tasks_minutes: parseInt(
      formData.get("break_between_tasks_minutes") as string,
      10
    ),
    break_between_subjects_minutes: parseInt(
      formData.get("break_between_subjects_minutes") as string,
      10
    ),
  };
  try {
    await updateSettings(data);
    revalidatePath("/settings");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function createNoGoZoneAction(
  formData: FormData
): Promise<{ error?: string }> {
  const label = formData.get("label") as string;
  const start_time = formData.get("start_time") as string;
  const end_time = formData.get("end_time") as string;
  const recurrence = formData.get("recurrence") as string;

  const data: Parameters<typeof createNoGoZone>[0] = { label, start_time, end_time };
  if (recurrence === "date") {
    data.date = (formData.get("date") as string) || null;
  } else {
    const days = formData.getAll("days_of_week").map((d) => parseInt(d as string, 10));
    data.days_of_week = days.length > 0 ? days : null;
  }

  try {
    await createNoGoZone(data);
    revalidatePath("/");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function deleteNoGoZoneAction(formData: FormData) {
  const id = formData.get("id") as string;
  await deleteNoGoZone(id);
  revalidatePath("/");
}

export async function logoutAction() {
  await logout();
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE_NAME);
  revalidatePath("/");
}

export async function disconnectGoogleAction(): Promise<{ error?: string }> {
  try {
    await disconnectGoogle();
    revalidatePath("/");
    revalidatePath("/settings");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function deleteAccountDataAction(): Promise<{ error?: string }> {
  try {
    await deleteAccountData();
    revalidatePath("/");
    revalidatePath("/settings");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}

export async function deleteAccountAction(): Promise<{ error?: string }> {
  try {
    await deleteAccount();
  } catch (e) {
    return { error: (e as Error).message };
  }
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE_NAME);
  redirect("/");
}
