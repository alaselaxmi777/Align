import React, { createContext, useContext, useEffect, useState } from "react";
import { Sun, Moon, Laptop } from "lucide-react";

export type Theme = "light" | "dark";
export type ThemePreference = "system" | "light" | "dark";

interface ThemeContextType {
  theme: Theme;
  preference: ThemePreference;
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
  setPreference: (p: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "dark",
  preference: "dark",
  toggleTheme: () => {},
  setTheme: () => {},
  setPreference: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(() => {
    if (typeof window !== "undefined") {
      const urlTheme = new URLSearchParams(window.location.search).get("theme");
      if (urlTheme === "light" || urlTheme === "dark") {
        return urlTheme;
      }
      const saved = localStorage.getItem("align_theme_preference");
      if (saved === "system" || saved === "light" || saved === "dark") {
        return saved;
      }
      const legacyTheme = localStorage.getItem("align_theme");
      if (legacyTheme === "light" || legacyTheme === "dark") {
        return legacyTheme;
      }
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
        return "light";
      }
    }
    return "dark";
  });

  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== "undefined") {
      const urlTheme = new URLSearchParams(window.location.search).get("theme");
      if (urlTheme === "light" || urlTheme === "dark") {
        return urlTheme;
      }
      if (preference === "system") {
        return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
      }
      return preference;
    }
    return "dark";
  });

  const applyThemeToDOM = (t: Theme) => {
    const root = document.documentElement;
    if (t === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
      root.setAttribute("data-theme", "dark");
    } else {
      root.classList.add("light");
      root.classList.remove("dark");
      root.setAttribute("data-theme", "light");
    }
  };

  useEffect(() => {
    let resolvedTheme: Theme = "dark";
    const urlTheme = new URLSearchParams(window.location.search).get("theme");
    if (urlTheme === "light" || urlTheme === "dark") {
      resolvedTheme = urlTheme;
    } else if (preference === "system") {
      resolvedTheme = window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
    } else {
      resolvedTheme = preference;
    }
    setThemeState(resolvedTheme);
    applyThemeToDOM(resolvedTheme);
    if (!urlTheme) {
      localStorage.setItem("align_theme_preference", preference);
      localStorage.setItem("align_theme", resolvedTheme);
    }
  }, [preference]);

  // Listen to OS theme changes when preference is "system"
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (e: MediaQueryListEvent) => {
      if (preference === "system") {
        const newTheme: Theme = e.matches ? "dark" : "light";
        setThemeState(newTheme);
        applyThemeToDOM(newTheme);
        localStorage.setItem("align_theme", newTheme);
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [preference]);

  const toggleTheme = () => {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";
    setPreferenceState(nextTheme);
    setThemeState(nextTheme);
  };

  const setTheme = (t: Theme) => {
    setPreferenceState(t);
    setThemeState(t);
  };

  const setPreference = (p: ThemePreference) => {
    setPreferenceState(p);
  };

  return (
    <ThemeContext.Provider value={{ theme, preference, toggleTheme, setTheme, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeToggle({ className = "", showLabel = false }: { className?: string; showLabel?: boolean }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`theme-toggle-btn ${className}`}
      title={`Switch to ${isDark ? "Light" : "Dark"} Mode`}
      aria-label={`Switch to ${isDark ? "Light" : "Dark"} Mode`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "7px",
        padding: "6px 11px",
        borderRadius: "9999px",
        border: "1px solid var(--border)",
        background: "var(--bg-card-glass)",
        color: "var(--text)",
        cursor: "pointer",
        transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      <span
        style={{
          display: "grid",
          placeItems: "center",
          color: isDark ? "var(--peach)" : "var(--lilac)",
          transition: "transform 0.3s ease",
          transform: isDark ? "rotate(0deg)" : "rotate(180deg)",
        }}
      >
        {isDark ? <Sun size={15} strokeWidth={2.2} /> : <Moon size={15} strokeWidth={2.2} />}
      </span>
      {showLabel && (
        <span style={{ fontSize: "12px", fontWeight: "600" }}>
          {isDark ? "Light" : "Dark"}
        </span>
      )}
    </button>
  );
}
