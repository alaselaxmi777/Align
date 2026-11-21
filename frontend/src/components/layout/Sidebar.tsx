import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  House,
  Compass,
  UserCheck,
  Users,
  Calendar,
  Target,
  MapPin,
  Globe,
  Bookmark,
  MessageSquare,
  Bell,
  UserRound,
  Settings,
  Shield,
  X,
  Sparkles,
  LucideIcon,
} from "lucide-react";

export interface SidebarItem {
  to: string;
  label: string;
  icon: LucideIcon;
  authOnly?: boolean;
  adminOnly?: boolean;
}

// Canonical Sidebar order strictly conforming to Acceptance Criteria:
// Dashboard, AI Discover, People, Communities, Events, Activities, Places, ALIGN MAP, Saved, Messages, Notifications, Profile, Settings, and Admin only for admins.
export const SIDEBAR_ITEMS: SidebarItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: House },
  { to: "/discover", label: "AI Discover", icon: Compass },
  { to: "/people", label: "People", icon: UserCheck },
  { to: "/communities", label: "Communities", icon: Users },
  { to: "/events", label: "Events", icon: Calendar },
  { to: "/activities", label: "Activities", icon: Target },
  { to: "/places", label: "Places", icon: MapPin },
  { to: "/map", label: "ALIGN MAP", icon: Globe },
  { to: "/saved", label: "Saved", icon: Bookmark, authOnly: true },
  { to: "/messages", label: "Messages", icon: MessageSquare, authOnly: true },
  { to: "/notifications", label: "Notifications", icon: Bell, authOnly: true },
  { to: "/profile", label: "Profile", icon: UserRound, authOnly: true },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/admin", label: "Admin", icon: Shield, adminOnly: true },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  unreadNotifications?: boolean;
}

export default function Sidebar({ open, onClose, unreadNotifications = false }: SidebarProps) {
  const location = useLocation();
  const loggedIn = Boolean(localStorage.getItem("align_token"));
  const userRole = localStorage.getItem("align_user_role") || "user";
  const isAdmin = userRole === "admin";

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex"
      role="dialog"
      aria-modal="true"
      aria-label="Sidebar Navigation Menu"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <aside
        className="relative flex flex-col w-72 max-w-[85vw] bg-[var(--bg-elev)] border-r border-[var(--border)] p-6 shadow-2xl z-10 overflow-y-auto"
      >
        <div className="flex items-center justify-between pb-5 mb-3 border-b border-[var(--border)]">
          <Link to={loggedIn ? "/dashboard" : "/"} onClick={onClose} className="flex items-center gap-2.5">
            <div className="logo-badge" aria-hidden="true">
              <Sparkles size={16} className="text-[#1C1126]" />
            </div>
            <span className="logo-wordmark text-lg">
              ALIGN<span className="dot">.</span>
            </span>
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card)] transition-colors"
            aria-label="Close Sidebar"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex flex-col gap-1 flex-1" aria-label="Sidebar Sections">
          {SIDEBAR_ITEMS.map((item) => {
            if (item.authOnly && !loggedIn) return null;
            if (item.adminOnly && !isAdmin) return null;

            const isActive = location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(item.to));
            const Icon = item.icon;

            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? "bg-[rgba(200,255,0,0.12)] text-[var(--lime)] font-bold shadow-sm"
                    : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-card)]"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon size={17} className={isActive ? "text-[var(--lime)]" : "text-[var(--text-muted)]"} />
                <span className="flex-1">{item.label}</span>
                {item.label === "Notifications" && unreadNotifications && (
                  <span className="w-2 h-2 rounded-full bg-[var(--danger)]" aria-label="Unread alerts indicator" />
                )}
                {item.adminOnly && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[rgba(239,68,68,0.15)] text-[var(--danger)]">
                    Admin
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="pt-4 mt-auto border-t border-[var(--border)] text-center text-[11px] text-[var(--text-muted)]">
          ALIGN Platform &copy; 2026
        </div>
      </aside>
    </div>
  );
}
