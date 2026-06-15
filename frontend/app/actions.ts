"use server";

import { revalidatePath } from "next/cache";
import { createTask, completeTask, deleteTask, runScheduler } from "@/lib/api";

export async function createTaskAction(formData: FormData) {
  const title = formData.get("title") as string;
  const subject = formData.get("subject") as string;
  const estimated_minutes = parseInt(
    formData.get("estimated_minutes") as string,
    10
  );
  await createTask({ title, subject, estimated_minutes });
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
