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
  updateSettings,
  logout,
  disconnectGoogle,
  deleteAccountData,
  deleteAccount,
  SESSION_COOKIE_NAME,
  type Priority,
  type Settings,
  type TimeTrackingMode,
} from "@/lib/api";

export async function createTaskAction(formData: FormData) {
  const title = formData.get("title") as string;
  const subject = formData.get("subject") as string;
  const estimated_minutes = parseInt(
    formData.get("estimated_minutes") as string,
    10
  );
  const due_date = (formData.get("due_date") as string) || null;
  const priority = (formData.get("priority") as Priority) || "medium";
  await createTask({ title, subject, estimated_minutes, due_date, priority });
  revalidatePath("/");
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
  };
  try {
    await updateSettings(data);
    revalidatePath("/settings");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
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
