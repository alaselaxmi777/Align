import { useState } from "react";
import {
  Bell,
  Bookmark,
  CalendarDays,
  Compass,
  Home,
  LogIn,
  LogOut,
  MessageCircle,
  Menu,
  X,
  Settings as SettingsIcon,
  Share2,
  Sparkles,
  Target,
  User as UserIcon,
  UserPlus,
  Users,
  Wrench,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ThemeToggle } from "../lib/theme";

export default function Topbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const loggedIn = Boolean(localStorage.getItem("align_token"));
  const userName = localStorage.getItem("align_user_name") || "Profile";

  function logout() {
    localStorage.removeItem("align_token");
    localStorage.removeItem("align_user_name");
    localStorage.removeItem("align_user_email");
    localStorage.removeItem("align_onboarded");
    navigate("/");
    window.location.reload();
  }

  const isActive = (path: string) => (location.pathname === path ? "nav-active" : "");

  return (
    <>
      <header className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <Link to="/" className="brand">
            <span className="brand-icon">
              <Sparkles size={18} />
            </span>
            <span className="logo-wordmark">
              ALIGN<span className="dot">.</span>
            </span>
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Link to="/discover" className={isActive("/discover")}>
            <Compass size={15} /> Discover
          </Link>
          <Link to="/people" className={isActive("/people")}>
            <Users size={15} /> People
          </Link>
          <Link to="/skills-hobbies" className={isActive("/skills-hobbies")}>
            <Wrench size={15} /> Skills
          </Link>
          <Link to="/goals-interests" className={isActive("/goals-interests")}>
            <Target size={15} /> Goals
          </Link>
          <Link to="/communities" className={isActive("/communities")}>
            <UserPlus size={15} /> Communities
          </Link>
          <Link to="/events" className={isActive("/events")}>
            <CalendarDays size={15} /> Events
          </Link>
          <Link to="/feed" className={isActive("/feed")}>
            <Share2 size={15} /> Feed
          </Link>

          {loggedIn && (
            <Link to="/messages" className={isActive("/messages")} title="Direct Messages">
              <MessageCircle size={15} />
            </Link>
          )}
          {loggedIn && (
            <Link to="/notifications" className={isActive("/notifications")} title="Notifications">
              <Bell size={15} />
            </Link>
          )}
          {loggedIn && (
            <Link to="/saved" className={isActive("/saved")} title="Saved Content">
              <Bookmark size={15} />
            </Link>
          )}
          {loggedIn && (
            <Link to="/profile" className={isActive("/profile")} style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <span className="story-ring" style={{ padding: "1.5px" }}>
                <span className="story-ring-inner" style={{ padding: "1px" }}>
                  <UserIcon size={13} style={{ color: "var(--primary-text)" }} />
                </span>
              </span>
              <span>Profile</span>
            </Link>
          )}
          {loggedIn && (
            <Link to="/settings" className={isActive("/settings")} title="Settings">
              <SettingsIcon size={15} />
            </Link>
          )}

          {/* Theme Toggle Button */}
          <div style={{ marginLeft: "4px" }}>
            <ThemeToggle />
          </div>

          {loggedIn ? (
            <button className="nav-button" onClick={logout} title="Sign Out" style={{ marginLeft: "4px" }}>
              <LogOut size={15} />
            </button>
          ) : (
            <Link className="nav-cta" to="/login" style={{ marginLeft: "8px" }}>
              <LogIn size={15} /> Sign in
            </Link>
          )}
        </nav>

        {/* Mobile Header Controls */}
        <div className="flex lg:hidden" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{
              background: "transparent",
              border: "1px solid var(--border-subtle)",
              borderRadius: "10px",
              padding: "6px 10px",
              color: "var(--primary-text)",
              cursor: "pointer",
              display: "grid",
              placeItems: "center",
            }}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div
          style={{
            position: "fixed",
            top: "68px",
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 49,
          }}
          onClick={() => setMobileMenuOpen(false)}
        >
          <div
            style={{
              background: "var(--bg-card)",
              borderBottom: "1px solid var(--border-subtle)",
              padding: "20px 24px",
              boxShadow: "var(--card-shadow)",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <Link
                to="/discover"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/discover")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <Compass size={16} /> Discover
              </Link>
              <Link
                to="/people"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/people")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <Users size={16} /> People
              </Link>
              <Link
                to="/skills-hobbies"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/skills-hobbies")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <Wrench size={16} /> Skills
              </Link>
              <Link
                to="/goals-interests"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/goals-interests")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <Target size={16} /> Goals
              </Link>
              <Link
                to="/communities"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/communities")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <UserPlus size={16} /> Communities
              </Link>
              <Link
                to="/events"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/events")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <CalendarDays size={16} /> Events
              </Link>
              <Link
                to="/feed"
                onClick={() => setMobileMenuOpen(false)}
                className={isActive("/feed")}
                style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
              >
                <Share2 size={16} /> Feed
              </Link>
              {loggedIn && (
                <Link
                  to="/saved"
                  onClick={() => setMobileMenuOpen(false)}
                  className={isActive("/saved")}
                  style={{ padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "8px" }}
                >
                  <Bookmark size={16} /> Saved
                </Link>
              )}
            </div>

            <div style={{ paddingTop: "12px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              {loggedIn ? (
                <>
                  <Link
                    to="/profile"
                    onClick={() => setMobileMenuOpen(false)}
                    style={{ fontWeight: "700", display: "flex", alignItems: "center", gap: "8px", color: "var(--primary-text)" }}
                  >
                    <UserIcon size={16} /> {userName}
                  </Link>
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      logout();
                    }}
                    style={{ background: "transparent", border: "none", color: "var(--secondary-text)", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                  >
                    <LogOut size={16} /> Sign out
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="nav-cta"
                  style={{ width: "100%", textAlign: "center" }}
                >
                  <LogIn size={15} /> Sign in
                </Link>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Instagram-style Mobile Bottom Navigation Bar */}
      <nav
        className="mobile-bottom-nav lg:hidden"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          height: "60px",
          background: "var(--bg-card)",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
          zIndex: 48,
          boxShadow: "0 -2px 10px rgba(0, 0, 0, 0.05)",
        }}
      >
        <Link
          to="/feed"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "2px",
            color: location.pathname === "/feed" ? "var(--primary-accent)" : "var(--secondary-text)",
            fontSize: "10px",
            fontWeight: location.pathname === "/feed" ? "700" : "500",
          }}
        >
          <Home size={20} strokeWidth={location.pathname === "/feed" ? 2.5 : 1.8} />
          <span>Feed</span>
        </Link>

        <Link
          to="/discover"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "2px",
            color: location.pathname === "/discover" ? "var(--primary-accent)" : "var(--secondary-text)",
            fontSize: "10px",
            fontWeight: location.pathname === "/discover" ? "700" : "500",
          }}
        >
          <Compass size={20} strokeWidth={location.pathname === "/discover" ? 2.5 : 1.8} />
          <span>Discover</span>
        </Link>

        <Link
          to="/communities"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "2px",
            color: location.pathname === "/communities" ? "var(--primary-accent)" : "var(--secondary-text)",
            fontSize: "10px",
            fontWeight: location.pathname === "/communities" ? "700" : "500",
          }}
        >
          <Users size={20} strokeWidth={location.pathname === "/communities" ? 2.5 : 1.8} />
          <span>Groups</span>
        </Link>

        <Link
          to="/events"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "2px",
            color: location.pathname === "/events" ? "var(--primary-accent)" : "var(--secondary-text)",
            fontSize: "10px",
            fontWeight: location.pathname === "/events" ? "700" : "500",
          }}
        >
          <CalendarDays size={20} strokeWidth={location.pathname === "/events" ? 2.5 : 1.8} />
          <span>Events</span>
        </Link>

        <Link
          to={loggedIn ? "/profile" : "/login"}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "2px",
            color: location.pathname === "/profile" ? "var(--primary-accent)" : "var(--secondary-text)",
            fontSize: "10px",
            fontWeight: location.pathname === "/profile" ? "700" : "500",
          }}
        >
          <UserIcon size={20} strokeWidth={location.pathname === "/profile" ? 2.5 : 1.8} />
          <span>Profile</span>
        </Link>
      </nav>
    </>
  );
}
