import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

export default function Footer() {
  return (
    <footer className="footer-canva">
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 rounded-md bg-[var(--lilac)] grid place-items-center text-[#1C1126] text-xs font-bold">
          <Sparkles size={11} />
        </div>
        <span className="font-bold text-[var(--text)] tracking-tight">
          align<span className="text-[var(--pink)]">.</span>
        </span>
        <span className="text-[var(--text-muted)] text-xs ml-2">
          · Find the people who get you.
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
        <Link to="/discover" className="hover:text-[var(--text)] transition-colors">
          Discover
        </Link>
        <Link to="/communities" className="hover:text-[var(--text)] transition-colors">
          Communities
        </Link>
        <Link to="/events" className="hover:text-[var(--text)] transition-colors">
          Events
        </Link>
        <Link to="/settings" className="hover:text-[var(--text)] transition-colors">
          Settings
        </Link>
      </div>
    </footer>
  );
}
