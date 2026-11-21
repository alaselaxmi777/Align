import { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  LogIn,
  Sparkles,
  UserRound,
  LogOut,
  Settings,
  Bookmark,
  MessageSquare,
  Menu,
} from "lucide-react";
import { ThemeToggle } from "../../lib/theme";
import { PRIMARY_NAV_ITEMS, MORE_NAV_ITEMS } from "./navItems";
import Sidebar from "./Sidebar";
import { SafeAvatar } from "../common/SafeImage";

interface TopbarProps {
  title?: string;
  unreadNotifications?: boolean;
}

export default function Topbar({ unreadNotifications = false }: TopbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  const loggedIn = Boolean(localStorage.getItem("align_token"));
  const avatarUrl = localStorage.getItem("align_user_avatar");
  const userName = localStorage.getItem("align_user_name") || "Profile";
  const userHandle = localStorage.getItem("align_user_handle") || "user";

  // Close popovers on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close menus on route change
  useEffect(() => {
    setMoreOpen(false);
    setProfileOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem("align_token");
    localStorage.removeItem("align_user_id");
    localStorage.removeItem("align_user_name");
    localStorage.removeItem("align_user_handle");
    localStorage.removeItem("align_user_avatar");
    localStorage.removeItem("align_user_role");
    navigate("/");
    window.location.reload();
  };

  return (
    <header className="topbar-canva" role="banner">
      {/* Brand Logo: Lilac badge with sparkle + ALIGN. with pink dot */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="p-1.5 -ml-1 rounded-xl text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card)] transition-colors"
          aria-label="Open Sidebar Navigation"
          title="Sidebar Navigation"
        >
          <Menu size={20} />
        </button>

        <Link to={loggedIn ? "/dashboard" : "/"} className="flex items-center gap-2.5 group">
          <div className="logo-badge group-hover:scale-105 transition-transform" aria-hidden="true">
            <Sparkles size={18} className="text-[#1C1126]" />
          </div>
          <span className="logo-wordmark">
            ALIGN<span className="dot">.</span>
          </span>
          <span className="text-[var(--text-muted)] text-xs font-medium ml-1 hidden sm:inline whitespace-nowrap">
            · Find the people who get you.
          </span>
        </Link>
      </div>

      {/* Center / Right: Primary Navigation Links */}
      <nav className="hidden md:flex items-center gap-1 xl:gap-1.5" aria-label="Main Navigation">
        {PRIMARY_NAV_ITEMS.map((item) => {
          const isActive = location.pathname.startsWith(item.to);
          const Icon = item.icon;
          const isExtended = item.to === "/goals/journey" || item.to === "/opportunities";
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`nav-link-top ${isExtended ? "hidden xl:inline-flex" : ""} ${isActive ? "active" : ""}`}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon size={16} className={isActive ? "text-[var(--lime)]" : "text-[var(--text-muted)]"} />
              <span>{item.label}</span>
            </Link>
          );
        })}

        {/* "More" Dropdown Menu */}
        <div className="relative" ref={moreRef}>
          <button
            type="button"
            onClick={() => setMoreOpen((v) => !v)}
            className={`nav-link-top ${moreOpen ? "bg-[var(--bg-card-glass)] text-[var(--text)]" : ""}`}
            aria-expanded={moreOpen}
            aria-haspopup="true"
          >
            <span>More</span>
            <ChevronDown size={14} className={`transition-transform duration-200 ${moreOpen ? "rotate-180" : ""}`} />
          </button>

          {moreOpen && (
            <div
              className="absolute top-full mt-2 left-0 w-64 p-2 rounded-[20px] bg-[var(--bg-elev)] border border-[var(--border)] shadow-2xl backdrop-blur-xl z-50 animate-in fade-in zoom-in-95 duration-150 grid grid-cols-1 gap-1"
              role="menu"
            >
              {MORE_NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.to;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-[12px] text-xs font-semibold transition-all ${
                      isActive
                        ? "bg-[rgba(216,245,106,0.12)] text-[var(--lime)]"
                        : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card-glass)]"
                    }`}
                    role="menuitem"
                  >
                    <Icon size={15} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </nav>

      {/* Far Right Actions */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Theme Toggle (Sun / Moon) */}
        <ThemeToggle />

        {loggedIn ? (
          <>
            {/* Messages */}
            <Link
              to="/messages"
              className="w-9 h-9 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--lilac)] grid place-items-center transition-all"
              aria-label="Messages"
            >
              <MessageSquare size={17} />
            </Link>

            {/* Notifications */}
            <Link
              to="/notifications"
              className="relative w-9 h-9 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--lilac)] grid place-items-center transition-all"
              aria-label="Notifications"
            >
              <Bell size={17} />
              {unreadNotifications && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--lime)] ring-2 ring-[var(--bg)]" />
              )}
            </Link>

            {/* User Profile Menu */}
            <div className="relative" ref={profileRef}>
              <button
                type="button"
                onClick={() => setProfileOpen((v) => !v)}
                className="flex items-center gap-2 p-1 rounded-full border border-[var(--border)] hover:border-[var(--lilac)] bg-[var(--bg-card-glass)] transition-all"
                aria-expanded={profileOpen}
                aria-haspopup="true"
              >
                <SafeAvatar
                  src={avatarUrl}
                  name={userName}
                  size={28}
                />
                <ChevronDown size={13} className="text-[var(--text-muted)] mr-1" />
              </button>

              {profileOpen && (
                <div
                  className="absolute right-0 top-full mt-2 w-56 p-2 rounded-[20px] bg-[var(--bg-elev)] border border-[var(--border)] shadow-2xl backdrop-blur-xl z-50 animate-in fade-in zoom-in-95 duration-150"
                  role="menu"
                >
                  <div className="px-3 py-2 border-b border-[var(--border)] mb-1">
                    <p className="text-xs font-bold text-[var(--text)] truncate">{userName}</p>
                    <p className="text-[11px] text-[var(--text-muted)] truncate">@{userHandle}</p>
                  </div>

                  <Link
                    to="/profile"
                    className="flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card-glass)]"
                    role="menuitem"
                  >
                    <UserRound size={15} />
                    <span>My Profile</span>
                  </Link>
                  <Link
                    to="/saved"
                    className="flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card-glass)]"
                    role="menuitem"
                  >
                    <Bookmark size={15} />
                    <span>Saved Items</span>
                  </Link>
                  <Link
                    to="/settings"
                    className="flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card-glass)]"
                    role="menuitem"
                  >
                    <Settings size={15} />
                    <span>Settings</span>
                  </Link>

                  <div className="border-t border-[var(--border)] my-1" />

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-[12px] text-xs font-semibold text-[var(--danger)] hover:bg-[rgba(255,107,107,0.1)] transition-all"
                    role="menuitem"
                  >
                    <LogOut size={15} />
                    <span>Log out</span>
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          /* Bordered "Sign in" button with icon on far right as specified */
          <Link
            to="/login"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] text-[var(--text)] hover:border-[var(--lilac)] hover:bg-[var(--bg-card-glass)] text-xs font-bold tracking-wide transition-all shadow-sm"
          >
            <LogIn size={14} className="text-[var(--lilac)]" />
            <span>Sign in</span>
          </Link>
        )}

        {/* Settings button right at the corner */}
        <Link
          to="/settings"
          className={`w-9 h-9 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--lilac)] grid place-items-center transition-all ${
            location.pathname === "/settings"
              ? "border-[var(--lime)] text-[var(--lime)] bg-[rgba(216,245,106,0.12)]"
              : ""
          }`}
          aria-label="Settings"
          title="Settings"
        >
          <Settings size={17} />
        </Link>
      </div>

      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        unreadNotifications={unreadNotifications}
      />
    </header>
  );
}
