import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/app/components/Breadcrumbs";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms that govern your use of Breadcrumbs.",
};

const h2 =
  "text-lg font-semibold text-zinc-900 dark:text-zinc-100 mt-8 mb-2";
const p = "text-sm sm:text-base text-zinc-700 dark:text-zinc-300 leading-relaxed";
const ul = "list-disc pl-6 text-sm sm:text-base text-zinc-700 dark:text-zinc-300 leading-relaxed space-y-1";
const a =
  "text-indigo-600 dark:text-indigo-400 underline underline-offset-2 hover:text-indigo-500";

export default function TermsOfServicePage() {
  return (
    <main id="main-content" className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Terms of Service" }]} />
      <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mb-1">
        Terms of Service
      </h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
        Effective date: August 11, 2026
      </p>

      <p className={p}>
        These Terms of Service (&ldquo;Terms&rdquo;) govern your use of
        Breadcrumbs (the &ldquo;Service&rdquo;), operated by Theodore Chen
        (&ldquo;we,&rdquo; &ldquo;us&rdquo;). By creating an account or using
        the Service, you agree to these Terms.
      </p>

      <h2 className={h2}>1. What Breadcrumbs does</h2>
      <p className={p}>
        Breadcrumbs reads your Google Calendar to find free time, and
        schedules tasks you enter into that free time by creating events on
        your calendar. It also learns from your task-completion history to
        improve its time estimates over time. It&rsquo;s a personal
        productivity tool — it is not a substitute for your own judgment
        about your schedule, deadlines, or commitments.
      </p>

      <h2 className={h2}>2. Your account</h2>
      <p className={p}>
        You need a Google Account to use Breadcrumbs, and you connect it via
        Google Sign-In. You&rsquo;re responsible for maintaining the security
        of your Google Account and for all activity that happens under your
        Breadcrumbs account. Let us know at{" "}
        <a className={a} href="mailto:theochen16+work@gmail.com">
          theochen16+work@gmail.com
        </a>{" "}
        if you suspect unauthorized use.
      </p>

      <h2 className={h2}>3. Acceptable use</h2>
      <p className={p}>You agree not to:</p>
      <ul className={ul}>
        <li>Use the Service for any unlawful purpose</li>
        <li>Attempt to disrupt, overload, or gain unauthorized access to the Service or other users&rsquo; data</li>
        <li>Reverse-engineer or misuse the Service in a way not intended by its ordinary use</li>
      </ul>
      <p className={`${p} mt-3`}>We may suspend or terminate accounts that violate these Terms.</p>

      <h2 className={h2}>4. Your data</h2>
      <p className={p}>
        You retain ownership of the tasks, settings, and other content you
        enter into Breadcrumbs. By using the Service, you give us permission
        to process that data as necessary to provide the Service (as
        described in our <Link className={a} href="/privacy">Privacy Policy</Link>).
      </p>
      <p className={`${p} mt-3`}>
        You can delete your data or account at any time from the Settings
        page — see the Privacy Policy for details on exactly what each option
        removes.
      </p>

      <h2 className={h2}>5. Calendar changes made on your behalf</h2>
      <p className={p}>
        When you run the scheduler or manually move a task, Breadcrumbs
        creates, moves, or deletes events on your connected Google Calendar.
        You&rsquo;re responsible for reviewing what gets scheduled.
        Breadcrumbs will not modify or delete calendar events it did not
        create itself, other than checking their times to avoid
        double-booking.
      </p>

      <h2 className={h2}>6. No warranty</h2>
      <p className={p}>
        The Service is provided &ldquo;as is,&rdquo; without warranties of
        any kind, express or implied. We do not guarantee that scheduling
        suggestions or time estimates will be accurate, that the Service will
        be uninterrupted or error-free, or that it will meet your specific
        needs.
      </p>

      <h2 className={h2}>7. Limitation of liability</h2>
      <p className={p}>
        To the maximum extent permitted by law, Theodore Chen will not be
        liable for any indirect, incidental, or consequential damages arising
        from your use of the Service, including missed deadlines, scheduling
        conflicts, or data loss. Our total liability for any claim arising
        from the Service is limited to the amount you paid us in the past 12
        months (which, for a free service, is zero).
      </p>

      <h2 className={h2}>8. Termination</h2>
      <p className={p}>
        You may stop using the Service and delete your account at any time.
        We may suspend or terminate your access if you violate these Terms,
        or discontinue the Service entirely with reasonable notice.
      </p>

      <h2 className={h2}>9. Changes to these Terms</h2>
      <p className={p}>
        We may update these Terms as the Service changes. We&rsquo;ll update
        the effective date above, and for material changes, we&rsquo;ll make
        reasonable efforts to notify you.
      </p>

      <h2 className={h2}>10. Governing law</h2>
      <p className={p}>
        These Terms are governed by the laws of Massachusetts, without regard
        to conflict-of-law principles.
      </p>

      <h2 className={h2}>11. Contact</h2>
      <p className={p}>
        Questions about these Terms:{" "}
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
