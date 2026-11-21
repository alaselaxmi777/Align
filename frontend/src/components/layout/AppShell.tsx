import React from "react";
import Topbar from "./Topbar";
import MobileNavigation from "./MobileNavigation";
import Footer from "./Footer";
import AIAssistantWidget from "../AIAssistantWidget";

interface AppShellProps {
  title?: string;
  children: React.ReactNode;
  unreadNotifications?: boolean;
  hideFooter?: boolean;
}

export default function AppShell({
  title,
  children,
  unreadNotifications = false,
  hideFooter = false,
}: AppShellProps) {
  return (
    <div className="shell min-h-screen flex flex-col bg-[var(--bg)] text-[var(--text)]">
      <Topbar title={title} unreadNotifications={unreadNotifications} />
      <main className="canva-content flex-1">
        {children}
        {!hideFooter && <Footer />}
      </main>
      <MobileNavigation />
      <AIAssistantWidget />
    </div>
  );
}
