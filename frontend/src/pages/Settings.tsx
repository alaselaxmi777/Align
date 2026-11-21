import { FormEvent, useEffect, useState } from "react";
import {
  AlertCircle,
  Bell,
  Camera,
  Check,
  CheckCircle2,
  ExternalLink,
  Eye,
  Instagram,
  Laptop,
  Loader2,
  Lock,
  LogOut,
  MapPin,
  Moon,
  Navigation,
  RefreshCw,
  Save,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Sun,
  Trash2,
  Unlink,
  X,
  Download,
  KeyRound,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import { api, InstagramStatus, SuggestedInterestItem, User } from "../lib/api";
import { ThemeToggle, useTheme } from "../lib/theme";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

export default function Settings() {
  const { theme, preference, setPreference } = useTheme();
  const toast = useToast();
  const [user, setUser] = useState<User | null>(null);
  const [privacyLevel, setPrivacyLevel] = useState("public");
  const [locationPrivacy, setLocationPrivacy] = useState("approximate");
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [eventReminders, setEventReminders] = useState(true);
  const [connectionAlerts, setConnectionAlerts] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  // Instagram Integration State
  const location = useLocation();
  const [igStatus, setIgStatus] = useState<InstagramStatus | null>(null);
  const [loadingIg, setLoadingIg] = useState(false);
  const [syncingIg, setSyncingIg] = useState(false);
  const [disconnectingIg, setDisconnectingIg] = useState(false);
  const [igFeedback, setIgFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [suggestedInterests, setSuggestedInterests] = useState<SuggestedInterestItem[]>([]);
  const [processingInterestId, setProcessingInterestId] = useState<number | null>(null);

  // Security, Password & Account Controls
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [loggingOutAll, setLoggingOutAll] = useState(false);
  const [exportingData, setExportingData] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [secMessage, setSecMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const navigate = useNavigate();
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (loggedIn) {
      api.me()
        .then((data) => {
          setUser(data);
          if (data.profile?.privacy_level) {
            setPrivacyLevel(data.profile.privacy_level);
          }
          if (data.profile?.location_privacy) {
            setLocationPrivacy(data.profile.location_privacy);
          }
        })
        .catch(() => {});

      loadInstagramData();
    }

    // Check query params for OAuth result
    const searchParams = new URLSearchParams(location.search);
    if (searchParams.get("instagram") === "connected") {
      setIgFeedback({
        type: "success",
        message: "Instagram account connected successfully! Media and visual interests are now syncing.",
      });
      navigate("/settings", { replace: true });
    } else if (searchParams.get("error")) {
      setIgFeedback({
        type: "error",
        message: searchParams.get("error_description") || searchParams.get("error") || "Instagram connection failed.",
      });
      navigate("/settings", { replace: true });
    }
  }, [loggedIn]);

  async function loadInstagramData() {
    setLoadingIg(true);
    try {
      const status = await api.getInstagramStatus();
      setIgStatus(status);
      if (status.connected) {
        const interests = await api.getSuggestedInterests("pending");
        setSuggestedInterests(interests);
      }
    } catch {
      // Ignored if disabled or unauthenticated
    } finally {
      setLoadingIg(false);
    }
  }

  async function handleConnectInstagram() {
    setLoadingIg(true);
    setIgFeedback(null);
    try {
      const res = await api.getInstagramConnectUrl();
      if (res.authorize_url) {
        window.location.href = res.authorize_url;
      }
    } catch (err: any) {
      setIgFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Unable to initiate Instagram connection.",
      });
      setLoadingIg(false);
    }
  }

  async function handleSyncInstagram() {
    setSyncingIg(true);
    setIgFeedback(null);
    try {
      const res = await api.syncInstagram();
      setIgFeedback({
        type: "success",
        message: `Synced ${res.synced_media_count} posts. ${res.suggested_interests_count} new interest suggestions found.`,
      });
      await loadInstagramData();
    } catch (err: any) {
      setIgFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to sync Instagram posts.",
      });
    } finally {
      setSyncingIg(false);
    }
  }

  async function handleDisconnectInstagram() {
    if (!window.confirm("Are you sure you want to disconnect Instagram? This will permanently delete your stored Instagram access tokens, cached media, and pending interest suggestions.")) {
      return;
    }
    setDisconnectingIg(true);
    setIgFeedback(null);
    try {
      await api.disconnectInstagram();
      setIgFeedback({
        type: "success",
        message: "Instagram account disconnected and all associated data permanently deleted.",
      });
      setSuggestedInterests([]);
      await loadInstagramData();
    } catch (err: any) {
      setIgFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to disconnect Instagram.",
      });
    } finally {
      setDisconnectingIg(false);
    }
  }

  async function handleToggleRecommendations(enabled: boolean) {
    if (!igStatus) return;
    try {
      const res = await api.updateInstagramPreferences({ recommendations_enabled: enabled });
      setIgStatus({ ...igStatus, recommendations_enabled: res.recommendations_enabled });
      if (enabled) {
        const interests = await api.getSuggestedInterests("pending");
        setSuggestedInterests(interests);
      }
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to update recommendations setting"));
    }
  }

  async function handleToggleProfileVisible(visible: boolean) {
    if (!igStatus) return;
    try {
      const res = await api.updateInstagramPreferences({ profile_visible: visible });
      setIgStatus({ ...igStatus, profile_visible: res.profile_visible });
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to update profile visibility setting"));
    }
  }

  async function handleAcceptInterest(id: number) {
    setProcessingInterestId(id);
    try {
      await api.acceptSuggestedInterest(id);
      setSuggestedInterests((prev) => prev.filter((i) => i.id !== id));
      toast.success("Interest accepted and added to your profile & discovery graph!");
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to accept interest"));
    } finally {
      setProcessingInterestId(null);
    }
  }

  async function handleRejectInterest(id: number) {
    setProcessingInterestId(id);
    try {
      await api.rejectSuggestedInterest(id);
      setSuggestedInterests((prev) => prev.filter((i) => i.id !== id));
      toast.info("Interest suggestion dismissed.");
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to reject interest"));
    } finally {
      setProcessingInterestId(null);
    }
  }

  async function handleSavePrivacy(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    try {
      await api.updateProfile({
        privacy_level: privacyLevel,
        location_privacy: locationPrivacy,
      });
      setSavedSuccess(true);
      toast.success("Privacy preferences saved successfully.");
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      toast.error(formatApiError(err, "Failed to save settings"));
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("align_token");
    localStorage.removeItem("align_user_name");
    localStorage.removeItem("align_user_email");
    localStorage.removeItem("align_user_avatar");
    localStorage.removeItem("align_onboarded");
    navigate("/");
    window.location.reload();
  }

  async function handleChangePassword(e: FormEvent) {
    e.preventDefault();
    if (!oldPassword || !newPassword) return;
    setChangingPassword(true);
    setSecMessage(null);
    try {
      const res = await api.changePassword({ old_password: oldPassword, new_password: newPassword });
      setSecMessage({ type: "success", text: res.message || "Password changed successfully. All other sessions revoked." });
      setOldPassword("");
      setNewPassword("");
      setShowChangePassword(false);
    } catch (err: any) {
      setSecMessage({ type: "error", text: err instanceof Error ? err.message : "Failed to change password." });
    } finally {
      setChangingPassword(false);
    }
  }

  async function handleLogoutAll() {
    if (!window.confirm("Are you sure you want to log out from all devices? You will need to sign in again.")) return;
    setLoggingOutAll(true);
    try {
      await api.logoutAll();
    } catch {
      // ignore
    } finally {
      localStorage.removeItem("align_token");
      localStorage.removeItem("align_user_name");
      localStorage.removeItem("align_user_email");
      localStorage.removeItem("align_user_avatar");
      localStorage.removeItem("align_onboarded");
      navigate("/login");
      window.location.reload();
    }
  }

  async function handleExportData() {
    setExportingData(true);
    setSecMessage(null);
    try {
      const data = await api.exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `align_user_export_${user?.id || "data"}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSecMessage({ type: "success", text: "GDPR archive exported successfully." });
    } catch (err: any) {
      setSecMessage({ type: "error", text: err instanceof Error ? err.message : "Failed to export data archive." });
    } finally {
      setExportingData(false);
    }
  }

  async function handleDeleteAccount() {
    const confirmation = window.prompt("WARNING: This will permanently delete your account, posts, connections, and all knowledge graph data. Type 'DELETE' to confirm:");
    if (confirmation !== "DELETE") {
      return;
    }
    setDeletingAccount(true);
    setSecMessage(null);
    try {
      await api.deleteAccount();
      localStorage.removeItem("align_token");
      localStorage.removeItem("align_user_name");
      localStorage.removeItem("align_user_email");
      localStorage.removeItem("align_user_avatar");
      localStorage.removeItem("align_onboarded");
      alert("Your account has been permanently deleted.");
      navigate("/");
      window.location.reload();
    } catch (err: any) {
      setSecMessage({ type: "error", text: err instanceof Error ? err.message : "Failed to delete account." });
      setDeletingAccount(false);
    }
  }

  return (
    <AppShell title="Settings">
      <p className="eyebrow">Make ALIGN yours</p>
      <h1 className="page-title">Settings</h1>

      {igFeedback && (
        <div
          style={{
            marginTop: "16px",
            padding: "12px 16px",
            borderRadius: "10px",
            border:
              igFeedback.type === "success"
                ? "1px solid rgba(16, 185, 129, 0.4)"
                : "1px solid rgba(239, 68, 68, 0.4)",
            backgroundColor:
              igFeedback.type === "success"
                ? "rgba(16, 185, 129, 0.1)"
                : "rgba(239, 68, 68, 0.1)",
            color: igFeedback.type === "success" ? "#10B981" : "#EF4444",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "13px",
            fontWeight: 500,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {igFeedback.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{igFeedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setIgFeedback(null)}
            style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: "2px" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {secMessage && (
        <div
          style={{
            marginTop: "16px",
            padding: "12px 16px",
            borderRadius: "10px",
            border:
              secMessage.type === "success"
                ? "1px solid rgba(16, 185, 129, 0.4)"
                : "1px solid rgba(239, 68, 68, 0.4)",
            backgroundColor:
              secMessage.type === "success"
                ? "rgba(16, 185, 129, 0.1)"
                : "rgba(239, 68, 68, 0.1)",
            color: secMessage.type === "success" ? "#10B981" : "#EF4444",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "13px",
            fontWeight: 500,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {secMessage.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{secMessage.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setSecMessage(null)}
            style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: "2px" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      <div className="panel" style={{ marginTop: "24px" }}>
        {/* Row 1: Account info */}
        <div className="setting-row">
          <div>
            <strong>Account settings</strong>
            <small>
              {loggedIn && user
                ? `Signed in as ${user.name} (${user.email})`
                : "Public preview session; sign in to persist changes."}
            </small>
          </div>
          {loggedIn ? (
            <span className="tag">Active Account</span>
          ) : (
            <Link to="/login" className="button primary">
              Sign in
            </Link>
          )}
        </div>

        {/* Row 2: Edit Profile */}
        <div className="setting-row">
          <div>
            <strong>Edit profile</strong>
            <small>Update your visible name, bio, craft, and skills for discovery.</small>
          </div>
          <Link to="/profile" className="button">
            Edit in profile
          </Link>
        </div>

        {/* Row 3: Appearance & Theme Preferences */}
        <div className="setting-row" style={{ alignItems: "flex-start", flexDirection: "column", gap: "12px" }}>
          <div>
            <strong>Appearance &amp; Theme</strong>
            <small>
              Currently active: <strong style={{ textTransform: "capitalize", color: "var(--lime)" }}>{theme} mode</strong> (using ALIGN Plum &amp; Warm Cream design system).
            </small>
          </div>
          <div className="flex items-center gap-1.5 p-1 rounded-full bg-[var(--bg-card-glass)] border border-[var(--border)]">
            <button
              type="button"
              onClick={() => setPreference("system")}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                preference === "system"
                  ? "bg-[var(--lime)] text-[var(--on-lime)] shadow-sm"
                  : "text-[var(--text-muted)] hover:text-[var(--text)]"
              }`}
            >
              <Laptop size={13} />
              <span>System</span>
            </button>
            <button
              type="button"
              onClick={() => setPreference("light")}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                preference === "light"
                  ? "bg-[var(--lime)] text-[var(--on-lime)] shadow-sm"
                  : "text-[var(--text-muted)] hover:text-[var(--text)]"
              }`}
            >
              <Sun size={13} />
              <span>Light</span>
            </button>
            <button
              type="button"
              onClick={() => setPreference("dark")}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                preference === "dark"
                  ? "bg-[var(--lime)] text-[var(--on-lime)] shadow-sm"
                  : "text-[var(--text-muted)] hover:text-[var(--text)]"
              }`}
            >
              <Moon size={13} />
              <span>Dark</span>
            </button>
          </div>
        </div>

        {/* Row 4: Privacy & Location Settings */}
        <div className="setting-row" style={{ alignItems: "flex-start", flexDirection: "column" }}>
          <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div>
              <strong>Privacy &amp; Location precision</strong>
              <small>Control discovery visibility and geographic precision for peer recommendations.</small>
            </div>
            {savedSuccess && (
              <span style={{ fontSize: "12px", color: "var(--success)", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                <CheckCircle2 size={14} /> Settings Saved
              </span>
            )}
          </div>

          <form onSubmit={handleSavePrivacy} style={{ width: "100%", display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Discovery Visibility */}
            <div>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "6px" }}>
                Profile Discovery Visibility
              </label>
              <select
                className="search"
                value={privacyLevel}
                onChange={(e) => setPrivacyLevel(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="public">Public — Discoverable by all community peers</option>
                <option value="community_only">Community Only — Visible only to members of your groups</option>
                <option value="private">Private — Hidden from search &amp; discovery</option>
              </select>
            </div>

            {/* Location Precision Options */}
            <div>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "8px" }}>
                Location Precision Level
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px" }}>
                {[
                  {
                    id: "exact",
                    title: "Exact GPS",
                    desc: "Full coordinates for precision nearby discovery",
                    tag: "Exact",
                    badgeColor: "rgba(239, 68, 68, 0.15)",
                    textColor: "#EF4444",
                  },
                  {
                    id: "approximate",
                    title: "Approximate (~1 km)",
                    desc: "0.01° grid snapping (~1.1 km) prevents triangulation",
                    tag: "Recommended",
                    badgeColor: "rgba(139, 92, 246, 0.15)",
                    textColor: "var(--accent)",
                  },
                  {
                    id: "city",
                    title: "City Level Only",
                    desc: "Snaps to metropolitan centroid; conceals neighborhood",
                    tag: "City Area",
                    badgeColor: "rgba(16, 185, 129, 0.15)",
                    textColor: "#10B981",
                  },
                  {
                    id: "off",
                    title: "Off / Hidden",
                    desc: "Distance hidden from peers; zero geo-bonus applied",
                    tag: "Private",
                    badgeColor: "rgba(107, 114, 128, 0.15)",
                    textColor: "#6B7280",
                  },
                ].map((opt) => (
                  <label
                    key={opt.id}
                    style={{
                      border: locationPrivacy === opt.id ? "2px solid var(--accent)" : "1px solid var(--border)",
                      borderRadius: "10px",
                      padding: "12px",
                      cursor: "pointer",
                      backgroundColor: locationPrivacy === opt.id ? "rgba(139, 92, 246, 0.05)" : "transparent",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 600, fontSize: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
                        <input
                          type="radio"
                          name="location_privacy"
                          value={opt.id}
                          checked={locationPrivacy === opt.id}
                          onChange={(e) => setLocationPrivacy(e.target.value)}
                        />
                        {opt.title}
                      </span>
                      <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 6px", borderRadius: "4px", backgroundColor: opt.badgeColor, color: opt.textColor }}>
                        {opt.tag}
                      </span>
                    </div>
                    <small style={{ color: "var(--muted)", fontSize: "12px", marginTop: "2px" }}>
                      {opt.desc}
                    </small>
                  </label>
                ))}
              </div>
            </div>

            {/* Live Preview: What others see based on your choice */}
            <div style={{
              backgroundColor: "rgba(255, 255, 255, 0.03)",
              border: "1px dashed var(--border)",
              borderRadius: "10px",
              padding: "14px 16px",
              marginTop: "4px",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--accent)", display: "inline-flex", alignItems: "center", gap: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <Eye size={14} /> Live Preview: What peers see in Discover &amp; Search
                </span>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                  Privacy-first API Guarantee
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", fontSize: "13px" }}>
                <div>
                  <span style={{ color: "var(--muted)" }}>Visible Location: </span>
                  <strong>
                    {locationPrivacy === "off"
                      ? `${(user?.profile?.location || "Pune").split(",")[0].trim()} (distance hidden)`
                      : locationPrivacy === "city" || locationPrivacy === "approximate"
                      ? (user?.profile?.location || "Pune").split(",")[0].trim()
                      : user?.profile?.location || "Pune, Maharashtra"}
                  </strong>
                </div>
                <span style={{ color: "var(--border)" }}>•</span>
                <div>
                  <span style={{ color: "var(--muted)" }}>Reported Distance: </span>
                  <strong style={{ color: locationPrivacy === "off" ? "#6B7280" : "var(--accent)" }}>
                    {locationPrivacy === "exact" && "2.4 km away (Exact distance)"}
                    {locationPrivacy === "approximate" && "< 5 km away (Coarse distance band)"}
                    {locationPrivacy === "city" && "Regional: < 15 km in City Area (Centroid)"}
                    {locationPrivacy === "off" && "Distance hidden by user"}
                  </strong>
                </div>
              </div>
              <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--muted)", display: "flex", alignItems: "center", gap: "6px" }}>
                <ShieldCheck size={14} style={{ color: "#10B981" }} />
                <span>ALIGN API never transmits raw GPS coordinates of other users to clients, preventing coordinate triangulation and location stalking.</span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit" className="button primary" disabled={saving || !loggedIn}>
                <Save size={14} style={{ marginRight: "6px" }} />
                {saving ? "Saving..." : "Save Privacy & Location"}
              </button>
            </div>
          </form>
        </div>

        {/* Row: Instagram Integration */}
        <div className="setting-row" style={{ alignItems: "flex-start", flexDirection: "column", gap: "16px" }}>
          <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "38px",
                  height: "38px",
                  borderRadius: "10px",
                  background: "linear-gradient(45deg, #F58529, #DD2A7B, #8134AF, #515BD4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                }}
              >
                <Instagram size={20} />
              </div>
              <div>
                <strong style={{ fontSize: "15px", display: "flex", alignItems: "center", gap: "6px" }}>
                  Instagram Integration
                </strong>
                <small>Connect your Instagram Business or Creator account for visual discovery and smart recommendations.</small>
              </div>
            </div>

            <div>
              {!igStatus ? (
                <span className="tag">Checking...</span>
              ) : !igStatus.enabled ? (
                <span className="tag" style={{ background: "rgba(107, 114, 128, 0.2)", color: "var(--muted)" }}>Feature Disabled</span>
              ) : igStatus.status === "connected" ? (
                <span className="tag" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10B981", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                  ● Connected (@{igStatus.username})
                </span>
              ) : igStatus.status === "reconnect_needed" ? (
                <span className="tag" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#EF4444", border: "1px solid rgba(239, 68, 68, 0.3)" }}>
                  ⚠ Reconnect Needed
                </span>
              ) : (
                <span className="tag">Not Connected</span>
              )}
            </div>
          </div>

          {/* Account Notice: Business/Creator constraint */}
          <div
            style={{
              width: "100%",
              padding: "10px 14px",
              borderRadius: "8px",
              backgroundColor: "rgba(139, 92, 246, 0.08)",
              border: "1px solid rgba(139, 92, 246, 0.2)",
              fontSize: "12px",
              color: "var(--muted)",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <Sparkles size={14} style={{ color: "var(--accent)", flexShrink: 0 }} />
            <span>
              <strong>Meta API Requirement:</strong> Works only with Instagram <strong>Business</strong> or <strong>Creator</strong> accounts. Personal accounts cannot be connected through the Meta Graph API.
            </span>
          </div>

          {/* Connection Actions */}
          {(!igStatus || !igStatus.connected) ? (
            <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginTop: "4px" }}>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
                Sync your media to showcase recent posts on your ALIGN profile and opt-in to improve recommendation matching.
              </p>
              <button
                type="button"
                className="button primary"
                onClick={handleConnectInstagram}
                disabled={loadingIg || !loggedIn || Boolean(igStatus && !igStatus.enabled)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "linear-gradient(45deg, #DD2A7B, #8134AF)",
                  border: "none",
                  color: "#fff",
                }}
              >
                {loadingIg ? <Loader2 size={14} className="spin" /> : <Instagram size={14} />}
                Connect Instagram
              </button>
            </div>
          ) : (
            <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "14px" }}>
              {/* Account summary banner */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "12px",
                  padding: "14px",
                  borderRadius: "10px",
                  backgroundColor: "rgba(255, 255, 255, 0.02)",
                  border: "1px solid var(--border)",
                  fontSize: "12px",
                }}
              >
                <div>
                  <span style={{ color: "var(--muted)", display: "block" }}>Instagram Handle</span>
                  <strong style={{ fontSize: "14px", color: "var(--accent)" }}>@{igStatus.username || "user"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--muted)", display: "block" }}>Account Type</span>
                  <strong>{igStatus.account_type || "Business/Creator"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--muted)", display: "block" }}>Synced Posts</span>
                  <strong>{igStatus.media_count} posts</strong>
                </div>
                <div>
                  <span style={{ color: "var(--muted)", display: "block" }}>Last Synchronized</span>
                  <strong>{igStatus.last_synced_at ? new Date(igStatus.last_synced_at).toLocaleDateString() + " " + new Date(igStatus.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Pending first sync"}</strong>
                </div>
              </div>

              {/* Action Buttons: Sync Now & Disconnect */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="button"
                  onClick={handleSyncInstagram}
                  disabled={syncingIg}
                  style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <RefreshCw size={13} className={syncingIg ? "spin" : ""} />
                  {syncingIg ? "Syncing..." : "Sync Media Now"}
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={handleDisconnectInstagram}
                  disabled={disconnectingIg}
                  style={{ color: "var(--error)", display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <Unlink size={13} />
                  {disconnectingIg ? "Disconnecting..." : "Disconnect Instagram"}
                </button>
              </div>

              {/* Preferences: Opt-in Toggles */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  paddingTop: "12px",
                  borderTop: "1px dashed var(--border)",
                }}
              >
                <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={igStatus.recommendations_enabled}
                    onChange={(e) => handleToggleRecommendations(e.target.checked)}
                    style={{ marginTop: "3px" }}
                  />
                  <div>
                    <strong style={{ fontSize: "13px", display: "block" }}>
                      Use my Instagram posts to improve recommendations
                    </strong>
                    <small style={{ color: "var(--muted)", fontSize: "12px" }}>
                      (Strictly Opt-In) Ingests captions and hashtags into 384-dimensional semantic embeddings. ALIGN clusters common themes into suggested interests for your explicit approval before using them in recommendations.
                    </small>
                  </div>
                </label>

                <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={igStatus.profile_visible}
                    onChange={(e) => handleToggleProfileVisible(e.target.checked)}
                    style={{ marginTop: "3px" }}
                  />
                  <div>
                    <strong style={{ fontSize: "13px", display: "block" }}>
                      Show on my profile
                    </strong>
                    <small style={{ color: "var(--muted)", fontSize: "12px" }}>
                      Displays your synced Instagram photos &amp; reels in an interactive 3-column media grid tab on your public ALIGN profile.
                    </small>
                  </div>
                </label>
              </div>

              {/* Pending Suggested Interests Review Section */}
              {suggestedInterests.length > 0 && (
                <div
                  style={{
                    backgroundColor: "rgba(139, 92, 246, 0.05)",
                    border: "1px solid rgba(139, 92, 246, 0.25)",
                    borderRadius: "10px",
                    padding: "14px 16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent)", display: "inline-flex", alignItems: "center", gap: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      <Sparkles size={14} /> Inferred Interests ({suggestedInterests.length})
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--muted)" }}>Requires your approval</span>
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 10px 0" }}>
                    We identified these potential passions from your Instagram posts. Accepted interests will be linked to your profile and the Neo4j discovery graph.
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {suggestedInterests.map((item) => (
                      <div
                        key={item.id}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "5px 10px",
                          borderRadius: "100px",
                          backgroundColor: "rgba(255, 255, 255, 0.06)",
                          border: "1px solid var(--border)",
                          fontSize: "12px",
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>#{item.interest}</span>
                        <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                          {Math.round(item.confidence_score * 100)}%
                        </span>
                        <button
                          type="button"
                          onClick={() => handleAcceptInterest(item.id)}
                          disabled={processingInterestId === item.id}
                          title="Accept and link to profile"
                          style={{
                            border: "none",
                            background: "rgba(16, 185, 129, 0.2)",
                            color: "#10B981",
                            borderRadius: "50%",
                            width: "20px",
                            height: "20px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            cursor: "pointer",
                            padding: 0,
                          }}
                        >
                          <Check size={12} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRejectInterest(item.id)}
                          disabled={processingInterestId === item.id}
                          title="Dismiss"
                          style={{
                            border: "none",
                            background: "rgba(239, 68, 68, 0.2)",
                            color: "#EF4444",
                            borderRadius: "50%",
                            width: "20px",
                            height: "20px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            cursor: "pointer",
                            padding: 0,
                          }}
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Privacy & Encryption Guarantee */}
              <div
                style={{
                  fontSize: "11px",
                  color: "var(--muted)",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  marginTop: "4px",
                }}
              >
                <Lock size={12} style={{ color: "#10B981" }} />
                <span>
                  <strong>Security Guarantee:</strong> Access tokens are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256). ALIGN never posts to your Instagram and never returns tokens to the browser.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Row 5: Notification Preferences */}
        <div className="setting-row">
          <div>
            <strong>Notification preferences</strong>
            <small>Manage event reminders, community alerts, and message notifications.</small>
          </div>
          <Link to="/notifications" className="button">
            View alerts
          </Link>
        </div>

        {/* Row 6: Help & Support */}
        <div className="setting-row">
          <div>
            <strong>Help &amp; support</strong>
            <small>Explore the ALIGN community guide and system architecture.</small>
          </div>
          <Link to="/" className="button">
            About ALIGN
          </Link>
        </div>

        {/* Row 7: Account Security & Password */}
        {loggedIn && (
          <div className="setting-row" style={{ display: "block" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: showChangePassword ? "12px" : "0" }}>
              <div>
                <strong style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <KeyRound size={16} /> Security &amp; Password
                </strong>
                <small>Update your account password or revoke active sessions across all devices.</small>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  type="button"
                  className="button"
                  onClick={() => setShowChangePassword((prev) => !prev)}
                >
                  {showChangePassword ? "Cancel" : "Change Password"}
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={handleLogoutAll}
                  disabled={loggingOutAll}
                  title="Revoke all active tokens across devices"
                >
                  {loggingOutAll ? <Loader2 size={14} className="spin" /> : "Log Out All Devices"}
                </button>
              </div>
            </div>

            {showChangePassword && (
              <form onSubmit={handleChangePassword} style={{ marginTop: "12px", borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
                      Current Password
                    </label>
                    <input
                      type="password"
                      value={oldPassword}
                      onChange={(e) => setOldPassword(e.target.value)}
                      placeholder="Enter current password"
                      required
                      style={{
                        width: "100%",
                        padding: "8px 12px",
                        borderRadius: "8px",
                        border: "1px solid var(--border)",
                        background: "var(--input-bg, rgba(255,255,255,0.05))",
                        color: "var(--text)",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
                      New Password (min 8 chars)
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter strong new password"
                      required
                      minLength={8}
                      style={{
                        width: "100%",
                        padding: "8px 12px",
                        borderRadius: "8px",
                        border: "1px solid var(--border)",
                        background: "var(--input-bg, rgba(255,255,255,0.05))",
                        color: "var(--text)",
                      }}
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  className="button primary"
                  disabled={changingPassword || !oldPassword || !newPassword}
                >
                  {changingPassword ? <Loader2 size={14} className="spin" /> : "Save New Password"}
                </button>
              </form>
            )}
          </div>
        )}

        {/* Row 8: Data Privacy & Export */}
        {loggedIn && (
          <div className="setting-row">
            <div>
              <strong style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Download size={16} /> Data Export (GDPR)
              </strong>
              <small>Download a complete JSON archive of your personal profile, preferences, and connections.</small>
            </div>
            <button
              type="button"
              className="button"
              onClick={handleExportData}
              disabled={exportingData}
            >
              {exportingData ? <Loader2 size={14} className="spin" /> : "Export Data Archive"}
            </button>
          </div>
        )}

        {/* Row 9: Account Access & Danger Zone */}
        <div className="setting-row">
          <div>
            <strong>Account access</strong>
            <small>
              {loggedIn ? "End current session or permanently delete your account." : "Sign in to access your saved profile."}
            </small>
          </div>
          {loggedIn ? (
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                className="button"
                onClick={handleLogout}
                style={{ color: "var(--text)", display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <LogOut size={14} /> Logout
              </button>
              <button
                type="button"
                className="button"
                onClick={handleDeleteAccount}
                disabled={deletingAccount}
                style={{
                  color: "var(--error, #EF4444)",
                  borderColor: "rgba(239, 68, 68, 0.4)",
                  backgroundColor: "rgba(239, 68, 68, 0.08)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Trash2 size={14} /> Delete Account
              </button>
            </div>
          ) : (
            <Link to="/login" className="button primary">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </AppShell>
  );
}
