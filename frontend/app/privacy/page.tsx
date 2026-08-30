import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/app/components/Breadcrumbs";
import { getLegalDoc } from "@/app/lib/legal";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Breadcrumbs collects, uses, and protects your information.",
  alternates: {
    canonical: "/privacy",
  },
};

export default function PrivacyPolicyPage() {
  const doc = getLegalDoc("privacy-policy.md");

  return (
    <main id="main-content" className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Privacy Policy" }]} />
      <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mb-1">
        {doc.title}
      </h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
        Effective date: {doc.effectiveDate}
      </p>

      <div dangerouslySetInnerHTML={{ __html: doc.html }} />

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
