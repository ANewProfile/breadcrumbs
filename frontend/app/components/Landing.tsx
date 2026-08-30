import Link from "next/link";

const faqs = [
  {
    q: "What calendar do I need to use Breadcrumbs?",
    a: "Google Calendar, connected via Google Sign-In is the only supported calendar at the moment.",
  },
  {
    q: "Will it touch events I didn't create?",
    a: "No. Breadcrumbs only reads your existing events to find free time. It only creates, moves, or deletes the events it made itself (labeled "[Breadcrumbs] ...").
  },
  {
    q: "Is my data secure?",
    a: "Connections are encrypted (HTTPS) and your data is encrypted at rest. See the Privacy Policy for the full picture.",
    link: { href: "/privacy", label: "Privacy Policy" },
  },
  {
    q: "Can I delete my data or account?",
    a: "Yes, any time, from Settings: disconnect Google Calendar, delete all your task data, or permanently delete your account.",
  },
  {
    q: "How much does Breadcrumbs cost?",
    a: "It's completely free to use for the time being.",
  },
];

export function Landing({ googleLoginUrl }: { googleLoginUrl: string }) {
  return (
    <>
      <main id="main-content" className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10 pb-24 sm:pb-10">
        <div className="flex flex-col items-center text-center mt-10 sm:mt-16 px-4">
          <h1 className="text-3xl sm:text-4xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight max-w-xl">
            Your to-do list, automatically scheduled around your life.
          </h1>
          <p className="text-sm sm:text-base text-zinc-500 dark:text-zinc-400 mt-3 max-w-md">
            Breadcrumbs reads your Google Calendar, finds your free time, and
            slots your tasks into it. Now you only have to decide what to do, not when.
          </p>
          <a
            href={googleLoginUrl}
            className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 rounded-lg transition-colors"
          >
            Sign in with Google
          </a>
          <a
            href="#faq"
            className="mt-4 text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 underline underline-offset-2 transition-colors"
          >
            Have questions? See the FAQ
          </a>
        </div>

        <section aria-labelledby="faq-heading" id="faq" className="mt-16 sm:mt-24 scroll-mt-20">
          <h2
            id="faq-heading"
            className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide mb-4"
          >
            Frequently asked questions
          </h2>
          <div className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800 border-t border-b border-zinc-200 dark:border-zinc-800">
            {faqs.map((item) => (
              <details key={item.q} className="group py-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-medium text-zinc-900 dark:text-zinc-100 marker:content-none [&::-webkit-details-marker]:hidden">
                  {item.q}
                  <span
                    aria-hidden="true"
                    className="shrink-0 text-zinc-400 dark:text-zinc-500 transition-transform group-open:rotate-45"
                  >
                    +
                  </span>
                </summary>
                <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {item.a}
                  {item.link && (
                    <>
                      {" "}
                      <Link
                        href={item.link.href}
                        className="text-indigo-600 dark:text-indigo-400 underline underline-offset-2 hover:text-indigo-500"
                      >
                        {item.link.label}
                      </Link>
                      .
                    </>
                  )}
                </p>
              </details>
            ))}
          </div>
        </section>
      </main>

      {/* Sticky mobile CTA: the hero button scrolls out of view on small
          screens once the FAQ is open, so keep sign-in reachable. */}
      <div className="sm:hidden fixed bottom-0 inset-x-0 z-40 border-t border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/95 backdrop-blur px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <a
          href={googleLoginUrl}
          className="block text-center text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 rounded-lg transition-colors"
        >
          Sign in with Google
        </a>
      </div>
    </>
  );
}
