import AppShell from "../components/layout/AppShell";
import { FileText, CheckCircle2, AlertTriangle, Scale, Ban } from "lucide-react";

export default function TermsOfService() {
  return (
    <AppShell title="Terms of Service">
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="text-center mb-10">
          <div className="inline-flex p-3 rounded-full bg-[rgba(168,85,247,0.1)] text-[var(--lilac)] mb-4">
            <FileText size={36} />
          </div>
          <h1 className="text-3xl font-extrabold text-[var(--text)] tracking-tight">Terms of Service</h1>
          <p className="text-sm text-[var(--text-muted)] mt-2">
            Effective Date: November 2026 · ALIGN Platform 2.0
          </p>
        </div>

        <div className="flex flex-col gap-8 text-[var(--text)] leading-relaxed text-sm">
          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <CheckCircle2 size={20} className="text-[var(--lilac)]" />
              1. Acceptance of Terms & Eligibility
            </h2>
            <p className="text-[var(--text-muted)]">
              By accessing or using ALIGN, you confirm that you are at least 18 years of age and legally capable of entering into binding agreements. If you do not meet the minimum age requirement or do not agree with these Terms, you must discontinue using the platform immediately.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <Ban size={20} className="text-[var(--lilac)]" />
              2. Acceptable Use & Community Safety
            </h2>
            <p className="text-[var(--text-muted)]">
              You agree not to upload, transmit, or share any content that is abusive, harassing, sexually explicit, defamatory, hateful, fraudulent, or infringing upon third-party intellectual property. Automated scraping, spamming, bot creation, and reverse engineering of ALIGN's recommendation algorithms are strictly prohibited.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <AlertTriangle size={20} className="text-[var(--lilac)]" />
              3. Content Moderation & Account Suspension
            </h2>
            <p className="text-[var(--text-muted)]">
              ALIGN enforces community standards through peer reporting and administrative review desks. We reserve the right to remove non-compliant content, issue formal warnings, or suspend/terminate accounts that violate platform safety rules without prior notice.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <Scale size={20} className="text-[var(--lilac)]" />
              4. Intellectual Property & User Content
            </h2>
            <p className="text-[var(--text-muted)]">
              You retain all intellectual property rights to the text, images, and videos you submit to ALIGN. By publishing content publicly, you grant ALIGN a limited, non-exclusive license to host, transcode, and display your media strictly in connection with the platform discovery features.
            </p>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
