import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/app/components/Breadcrumbs";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Breadcrumbs collects, uses, and protects your information.",
};

const h2 =
  "text-lg font-semibold text-zinc-900 dark:text-zinc-100 mt-8 mb-2";
const p = "text-sm sm:text-base text-zinc-700 dark:text-zinc-300 leading-relaxed";
const ul = "list-disc pl-6 text-sm sm:text-base text-zinc-700 dark:text-zinc-300 leading-relaxed space-y-1";
const a =
  "text-indigo-600 dark:text-indigo-400 underline underline-offset-2 hover:text-indigo-500";

export default function PrivacyPolicyPage() {
  return (
    <main id="main-content" className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Privacy Policy" }]} />
      <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mb-1">
        Privacy Policy
      </h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
        Effective date: August 11, 2026
      </p>

      <p className={p}>
        This Privacy Policy explains what information Breadcrumbs
        (&ldquo;Breadcrumbs,&rdquo; &ldquo;we,&rdquo; &ldquo;us&rdquo;) collects, how we use it, and the
        choices you have. Breadcrumbs is a personal task-scheduling tool that
        reads your Google Calendar to find free time and automatically
        schedules your tasks into it.
      </p>
      <p className={`${p} mt-3`}>
        If you have questions about this policy, contact us at{" "}
        <a className={a} href="mailto:theochen16+work@gmail.com">
          theochen16+work@gmail.com
        </a>
        .
      </p>

      <h2 className={h2}>1. Information we collect</h2>
      <p className={p}>
        <strong>From your Google Account (via Google Sign-In):</strong>
      </p>
      <ul className={ul}>
        <li>Your name, email address, and profile picture</li>
        <li>
          A unique Google account identifier, used to recognize you when you
          sign in
        </li>
      </ul>
      <p className={`${p} mt-3`}>
        <strong>From Google Calendar (only if you connect it):</strong>
      </p>
      <ul className={ul}>
        <li>Read access to your calendar events, used solely to compute your free time</li>
        <li>
          Write access limited to events Breadcrumbs itself creates on your
          behalf (labeled &ldquo;[Breadcrumbs] ...&rdquo;) — Breadcrumbs does not read
          the content of, modify, or delete events it did not create, beyond
          checking their start/end times to avoid double-booking you
        </li>
      </ul>
      <p className={`${p} mt-3`}>
        <strong>Information you provide directly:</strong>
      </p>
      <ul className={ul}>
        <li>Tasks you create: title, subject, estimated time, due date, priority</li>
        <li>Actual time a task took, if you choose to record it (manually or via the in-app timer)</li>
        <li>
          Your scheduling preferences (study hours, timezone, how much of one
          subject you want scheduled back-to-back, etc.)
        </li>
      </ul>
      <p className={`${p} mt-3`}>
        <strong>Automatically collected:</strong>
      </p>
      <ul className={ul}>
        <li>A session cookie that keeps you signed in. It is not used for tracking or advertising.</li>
      </ul>
      <p className={`${p} mt-3`}>
        We do not collect payment information, and we do not use analytics or
        advertising trackers.
      </p>

      <h2 className={h2}>2. How we use your information</h2>
      <p className={p}>We use your information solely to operate Breadcrumbs for you:</p>
      <ul className={ul}>
        <li>To read your calendar and find blocks of free time</li>
        <li>To create, move, or remove the calendar events Breadcrumbs schedules on your behalf</li>
        <li>To learn from your task-completion history and improve how we estimate how long your future tasks will take</li>
        <li>To keep you signed in and associate your tasks/settings with your account</li>
      </ul>
      <p className={`${p} mt-3`}>
        <strong>
          Breadcrumbs&rsquo; use and transfer of information received from
          Google APIs to any other app adheres to the{" "}
          <a
            className={a}
            href="https://developers.google.com/terms/api-services-user-data-policy"
            target="_blank"
            rel="noopener noreferrer"
          >
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements.
        </strong>{" "}
        We do not use your Google data for advertising, and we do not allow
        humans to read it except as necessary for security, legal compliance,
        or with your consent.
      </p>

      <h2 className={h2}>3. How we store and share your information</h2>
      <p className={p}>
        Your data is stored in MongoDB Atlas, a third-party database
        provider, which encrypts data at rest and in transit. We do not sell
        your information, and we do not share it with third parties except:
      </p>
      <ul className={ul}>
        <li>With Google, to the extent necessary to read/write your calendar as described above</li>
        <li>With our database provider (MongoDB Atlas), solely to store your data on our behalf</li>
        <li>If required by law, or to protect the rights, safety, or property of Breadcrumbs or others</li>
      </ul>

      <h2 className={h2}>4. Your controls</h2>
      <p className={p}>From the Settings page in the app, you can at any time:</p>
      <ul className={ul}>
        <li>
          <strong>Disconnect Google Calendar</strong> — revokes our access to
          your calendar (including on Google&rsquo;s side) without deleting
          your tasks or account
        </li>
        <li>
          <strong>Delete all your data</strong> — permanently deletes your
          tasks and settings, while keeping your account and calendar
          connection
        </li>
        <li>
          <strong>Delete your account</strong> — permanently deletes your
          account, tasks, settings, and disconnects Google Calendar; this
          cannot be undone
        </li>
      </ul>
      <p className={`${p} mt-3`}>
        You can also revoke Breadcrumbs&rsquo; access at any time directly
        from your{" "}
        <a
          className={a}
          href="https://myaccount.google.com/permissions"
          target="_blank"
          rel="noopener noreferrer"
        >
          Google Account permissions page
        </a>
        .
      </p>

      <h2 className={h2}>5. Data retention</h2>
      <p className={p}>
        We keep your information for as long as your account is active, or
        until you delete it using the controls above. Deleted data is removed
        from our production database; it is not recoverable once deleted.
      </p>

      <h2 className={h2}>6. Children&rsquo;s privacy</h2>
      <p className={p}>
        Breadcrumbs is not directed at, and is not knowingly used by,
        children under 13. If you believe a child has provided us
        information, contact us at{" "}
        <a className={a} href="mailto:theochen16+work@gmail.com">
          theochen16+work@gmail.com
        </a>{" "}
        and we will delete it.
      </p>

      <h2 className={h2}>7. Security</h2>
      <p className={p}>
        We use reasonable technical and organizational measures to protect
        your information, including encrypted connections (HTTPS) and
        encrypted storage. No method of transmission or storage is 100%
        secure, and we cannot guarantee absolute security.
      </p>

      <h2 className={h2}>8. Changes to this policy</h2>
      <p className={p}>
        We may update this policy as Breadcrumbs changes. We&rsquo;ll update
        the effective date above, and for material changes, we&rsquo;ll make
        reasonable efforts to notify you (e.g., via email or an in-app
        notice).
      </p>

      <h2 className={h2}>9. Contact</h2>
      <p className={p}>
        Questions or requests about your data:{" "}
        <a className={a} href="mailto:theochen16+work@gmail.com">
          theochen16+work@gmail.com
        </a>
      </p>

      <p className="mt-10">
        <Link
          href="/"
          className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
        >
          &larr; Back to Breadcrumbs
        </Link>
      </p>
    </main>
  );
}
