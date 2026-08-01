"use server";

import { revalidatePath } from "next/cache";
import {
  createTask,
  completeTask,
  deleteTask,
  runScheduler,
  updateSettings,
  type Priority,
  type Settings,
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

export async function completeTaskAction(formData: FormData) {
  const id = formData.get("id") as string;
  const actual_minutes = parseInt(
    formData.get("actual_minutes") as string,
    10
  );
  await completeTask(id, actual_minutes);
  revalidatePath("/");
}

export async function deleteTaskAction(formData: FormData) {
  const id = formData.get("id") as string;
  await deleteTask(id);
  revalidatePath("/");
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
  };
  try {
    await updateSettings(data);
    revalidatePath("/settings");
    return {};
  } catch (e) {
    return { error: (e as Error).message };
  }
}
