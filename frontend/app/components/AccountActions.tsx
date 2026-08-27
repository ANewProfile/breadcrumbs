"use client";

import { useState, useTransition } from "react";
import {
  disconnectGoogleAction,
  deleteAccountDataAction,
  deleteAccountAction,
} from "@/app/actions";

export function ConfirmAction({
  title,
  description,
  confirmLabel,
  confirmingLabel,
  action,
  tone = "neutral",
  typedConfirmationPhrase,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  confirmingLabel: string;
  action: () => Promise<{ error?: string; message?: string }>;
  tone?: "neutral" | "danger";
  /** When set, adds a third confirmation step: the exact phrase must be typed
   * before the final button becomes clickable. Reserved for the most severe
   * actions — most confirmations only need the two-step reveal-then-click. */
  typedConfirmationPhrase?: string;
}) {
  const [confirming, setConfirming] = useState(false);
  const [typedText, setTypedText] = useState("");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [doneMessage, setDoneMessage] = useState<string | null>(null);

  const typedMatches =
    !typedConfirmationPhrase ||
    typedText.trim().toLowerCase() === typedConfirmationPhrase.toLowerCase();

  function handleConfirm() {
    setError(null);
    startTransition(async () => {
      const result = await action();
      if (result.error) {
        setError(result.error);
      } else {
        setDoneMessage(result.message ?? "Done.");
        setConfirming(false);
        setTypedText("");
      }
    });
  }

  return (
    <div className="p-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{title}</p>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">{description}</p>
        </div>
        {!confirming && (
          <button
            type="button"
            aria-expanded={false}
            onClick={() => {
              setConfirming(true);
              setError(null);
              setDoneMessage(null);
              setTypedText("");
            }}
            className={`text-sm px-3 py-1.5 rounded-lg transition-colors shrink-0 ${
              tone === "danger"
                ? "bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900"
                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700"
            }`}
          >
            {confirmLabel}
          </button>
        )}
      </div>

      {confirming && (
        <div className="mt-3 flex flex-col gap-3">
          {typedConfirmationPhrase && (
            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              Type &ldquo;{typedConfirmationPhrase}&rdquo; to confirm
              <input
                type="text"
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                autoFocus
                autoComplete="off"
                className="bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 rounded-lg px-3 py-1.5 text-sm w-full max-w-xs focus:outline-none focus:ring-2 focus:ring-red-400"
              />
            </label>
          )}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleConfirm}
              disabled={pending || !typedMatches}
              className={`text-sm px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors ${
                tone === "danger"
                  ? "bg-red-600 hover:bg-red-500 text-white"
                  : "bg-zinc-900 dark:bg-zinc-100 hover:bg-zinc-700 dark:hover:bg-zinc-300 text-white dark:text-zinc-900"
              }`}
            >
              {pending ? confirmingLabel : `Yes, ${confirmLabel.toLowerCase()}`}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {doneMessage && (
        <p role="status" className="mt-2 text-sm text-green-600 dark:text-green-400">
          {doneMessage}
        </p>
      )}
      {error && <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}

export function AccountActions({
  googleConnected,
  googleLoginUrl,
}: {
  googleConnected: boolean;
  googleLoginUrl: string;
}) {
  return (
    <div className="mt-8 border border-zinc-200 dark:border-zinc-700 rounded-xl overflow-hidden">
      <div className="bg-zinc-50 dark:bg-zinc-900 px-4 py-3 border-b border-zinc-200 dark:border-zinc-700">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide">
          Account
        </h2>
      </div>
      <div className="divide-y divide-zinc-200 dark:divide-zinc-800">
        {googleConnected ? (
          <ConfirmAction
            title="Disconnect Google Calendar"
            description="Breadcrumbs will no longer be able to read your calendar or schedule tasks until you reconnect."
            confirmLabel="Disconnect"
            confirmingLabel="Disconnecting…"
            action={disconnectGoogleAction}
          />
        ) : (
          <div className="p-4 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Google Calendar</p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
                Not connected — scheduling won&apos;t work until you reconnect.
              </p>
            </div>
            <a
              href={googleLoginUrl}
              className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg transition-colors shrink-0"
            >
              Connect Google Calendar
            </a>
          </div>
        )}

        <ConfirmAction
          title="Delete all my data"
          description="Removes all your tasks and settings. Your account stays and Google Calendar stays connected."
          confirmLabel="Delete data"
          confirmingLabel="Deleting…"
          action={deleteAccountDataAction}
          tone="danger"
        />

        <ConfirmAction
          title="Delete my account"
          description="Permanently deletes your account, tasks, and settings, and disconnects Google Calendar. This can't be undone."
          confirmLabel="Delete account"
          confirmingLabel="Deleting…"
          action={deleteAccountAction}
          typedConfirmationPhrase="delete my account"
          tone="danger"
        />
      </div>
    </div>
  );
}
