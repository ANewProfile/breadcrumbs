import { redirect } from "next/navigation";
import { fetchSettings, fetchCurrentUser, BASE } from "@/lib/api";
import { SettingsForm } from "@/app/components/SettingsForm";
import { AccountActions } from "@/app/components/AccountActions";

export default async function SettingsPage() {
  const user = await fetchCurrentUser();
  if (!user) {
    redirect("/");
  }

  const settings = await fetchSettings();

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mb-1">
        Settings
      </h1>
      <p className="text-sm sm:text-base text-zinc-500 dark:text-zinc-400 mb-6 sm:mb-8">
        Controls how the scheduler picks free time and paces your workload.
      </p>

      <SettingsForm settings={settings} />
      <AccountActions
        googleConnected={user.google_connected}
        googleLoginUrl={`${BASE}/auth/google/login`}
      />
    </main>
  );
}
