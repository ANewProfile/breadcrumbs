"use client";

import { deleteFutureSchoolEventsAction } from "@/app/actions";
import { ConfirmAction } from "@/app/components/AccountActions";

export function DeleteSchoolEventsAction() {
  return (
    <section className="border border-zinc-200 dark:border-zinc-700 rounded-xl overflow-hidden">
      <div className="bg-zinc-50 dark:bg-zinc-900 px-4 py-3 border-b border-zinc-200 dark:border-zinc-700">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide">
          Manage school calendar events
        </h2>
      </div>
      <ConfirmAction
        title="Delete future school events"
        description="Removes every upcoming calendar event this tool created (anything ending in “[SCHOOL]”). Past events and everything else on your calendar are left alone."
        confirmLabel="Delete future events"
        confirmingLabel="Deleting…"
        action={deleteFutureSchoolEventsAction}
        tone="danger"
      />
    </section>
  );
}
