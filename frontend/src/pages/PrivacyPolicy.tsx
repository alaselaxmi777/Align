import AppShell from "../components/layout/AppShell";
import { Shield, Lock, Eye, MapPin, Database, UserCheck } from "lucide-react";

export default function PrivacyPolicy() {
  return (
    <AppShell title="Privacy Policy">
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="text-center mb-10">
          <div className="inline-flex p-3 rounded-full bg-[rgba(168,85,247,0.1)] text-[var(--lilac)] mb-4">
            <Shield size={36} />
          </div>
          <h1 className="text-3xl font-extrabold text-[var(--text)] tracking-tight">Privacy Policy</h1>
          <p className="text-sm text-[var(--text-muted)] mt-2">
            Last Updated: November 2026 · ALIGN Platform 2.0
          </p>
        </div>

        <div className="flex flex-col gap-8 text-[var(--text)] leading-relaxed text-sm">
          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <UserCheck size={20} className="text-[var(--lilac)]" />
              1. 18+ Young Adult Policy & Access Restrictions
            </h2>
            <p className="text-[var(--text-muted)]">
              ALIGN is designed strictly for adults aged 18 and older. We do not knowingly collect, store, or process personal information from minors. Accounts identified as belonging to individuals under 18 will be promptly closed and their associated data permanently removed.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <Eye size={20} className="text-[var(--lilac)]" />
              2. EXIF & Metadata Stripping
            </h2>
            <p className="text-[var(--text-muted)]">
              When you upload photos, carousels, or video reels to ALIGN, our automated media processing pipeline removes all embedded Exchangeable Image File Format (EXIF) and device metadata, including camera hardware serials, timestamps, and embedded GPS coordinates, before files are encoded into WebP/MP4 formats.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <MapPin size={20} className="text-[var(--lilac)]" />
              3. Geospatial Obfuscation (Coarse Grid)
            </h2>
            <p className="text-[var(--text-muted)]">
              We never track, broadcast, or store exact GPS telemetry for user accounts. Regional discovery across Maharashtra (Pune, Mumbai, Kolhapur, Nagpur, etc.) relies solely on coarse city-level representations or obfuscated grid bands (e.g., "Within 25 km"). Users may also select the "Hidden" privacy level at any time in Settings.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <Lock size={20} className="text-[var(--lilac)]" />
              4. Data Retention & Account Deletion
            </h2>
            <p className="text-[var(--text-muted)]">
              You maintain complete ownership of your personal content and profile data. You have the right to request full export or permanent deletion of your account and all associated posts, reels, comments, and semantic vectors at any time via Settings or by submitting an account deletion request.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-[var(--surface)] border border-[var(--border)]">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <Database size={20} className="text-[var(--lilac)]" />
              5. Third-Party Integrations & Google Sign-In
            </h2>
            <p className="text-[var(--text-muted)]">
              When you sign in with Google OAuth, we only access your basic public profile information (name, email address, and avatar URL) to establish your account. We never access your private emails, Google Drive documents, or contacts.
            </p>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
