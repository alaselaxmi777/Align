import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  House,
  Compass,
  Users,
  Calendar,
  MoreHorizontal,
  X,
  Target,
  Briefcase,
  MapPin,
  UserCheck,
  Sparkles,
  MessageSquare,
  Film,
  Award,
  FolderGit2,
  Bot,
  Settings,
  UserRound,
} from "lucide-react";
import { ThemeToggle } from "../../lib/theme";

export default function MobileNavigation() {
  const location = useLocation();
  const [sheetOpen, setSheetOpen] = useState(false);
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (!sheetOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSheetOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [sheetOpen]);

  const primaryTabs = [
    { to: loggedIn ? "/dashboard" : "/", label: "Home", icon: House },
    { to: "/feed", label: "Posts", icon: MessageSquare },
    { to: "/reels", label: "Reels", icon: Film },
    { to: "/discover", label: "Discover", icon: Compass },
  ];

  const sheetItems = [
    { to: "/communities", label: "Communities", icon: Users },
    { to: "/events", label: "Events", icon: Calendar },
    { to: "/goals/journey", label: "Goal Journey", icon: Target },
    { to: "/opportunities", label: "Opportunities", icon: Briefcase },
    { to: "/places", label: "Places", icon: MapPin },
    { to: "/people", label: "People", icon: UserCheck },
    { to: "/circles", label: "Circles", icon: Sparkles },
    { to: "/projects", label: "Collaborate", icon: FolderGit2 },
    { to: "/achievements", label: "Achievements", icon: Award },
    { to: "/assistant", label: "AI Assistant", icon: Bot },
    { to: "/settings", label: "Settings", icon: Settings },
    { to: loggedIn ? "/profile" : "/login", label: loggedIn ? "Profile" : "Sign In", icon: UserRound },
  ];

  return (
    <>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {primaryTabs.map((item) => {
          const isActive =
            item.to === "/" || item.to === "/dashboard"
              ? location.pathname === item.to
              : location.pathname.startsWith(item.to);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={isActive ? "active" : ""}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon size={20} aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}

        {/* More Tab */}
        <button
          type="button"
          onClick={() => setSheetOpen(true)}
          className={sheetOpen ? "active" : ""}
          aria-label="Open more menu"
        >
          <MoreHorizontal size={20} aria-hidden="true" />
          <span>More</span>
        </button>
      </nav>

      {/* Slide-up Bottom Sheet for "More" */}
      {sheetOpen && (
        <div className="fixed inset-0 z-[60] flex flex-col justify-end">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={() => setSheetOpen(false)}
            aria-hidden="true"
          />

          {/* Sheet Content */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label="More navigation options"
            className="relative z-10 w-full max-h-[80vh] overflow-y-auto bg-[var(--bg-elev)] border-t border-[var(--border)] rounded-t-[32px] p-6 shadow-2xl animate-in slide-in-from-bottom duration-250"
          >
            <div className="flex items-center justify-between pb-4 border-b border-[var(--border)] mb-4">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[var(--lime)]" />
                <h3 className="font-bold text-base text-[var(--text)]">More Pages</h3>
              </div>
              <div className="flex items-center gap-3">
                <ThemeToggle />
                <button
                  type="button"
                  onClick={() => setSheetOpen(false)}
                  className="w-8 h-8 rounded-full bg-[var(--bg-card-glass)] border border-[var(--border)] grid place-items-center text-[var(--text-muted)]"
                  aria-label="Close menu"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              {sheetItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.to);
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={() => setSheetOpen(false)}
                    className={`flex items-center gap-3 p-3 rounded-[16px] border text-xs font-semibold transition-all ${
                      isActive
                        ? "bg-[rgba(216,245,106,0.12)] border-[var(--lime)] text-[var(--lime)]"
                        : "bg-[var(--bg-card-glass)] border-[var(--border)] text-[var(--text)] hover:border-[var(--lilac)]"
                    }`}
                  >
                    <Icon size={18} className="text-[var(--lilac)] shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
