import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { fetchSchoolSchedule, fetchCurrentUser, BASE } from "@/lib/api";
import { SchoolScheduleForm } from "@/app/components/SchoolScheduleForm";
import { GenerateCalendarForm } from "@/app/components/GenerateCalendarForm";
import { AddSnowDayAction } from "@/app/components/AddSnowDayAction";
import { DeleteSchoolEventsAction } from "@/app/components/DeleteSchoolEventsAction";
import { Breadcrumbs } from "@/app/components/Breadcrumbs";

export const metadata: Metadata = {
  title: "School Schedule",
  description: "Set up your 6-day rotating school schedule and add it to Google Calendar.",
};

export default async function ScheduleInsertPage() {
  const user = await fetchCurrentUser();
  if (!user) {
    redirect("/");
  }

  const schedule = await fetchSchoolSchedule();

  return (
    <main id="main-content" className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "School Schedule" }]} />
      <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mb-1">
        School Schedule
      </h1>
      <p className="text-sm sm:text-base text-zinc-500 dark:text-zinc-400 mb-6 sm:mb-8">
        Set up your 6-day rotating schedule once, then add it to Google Calendar for any date
        range.
      </p>

      <div className="flex flex-col gap-6">
        <SchoolScheduleForm schedule={schedule} />
        <GenerateCalendarForm
          googleConnected={user.google_connected}
          googleLoginUrl={`${BASE}/auth/google/login`}
        />
        {user.google_connected && <AddSnowDayAction />}
        {user.google_connected && <DeleteSchoolEventsAction />}
      </div>
    </main>
  );
}
