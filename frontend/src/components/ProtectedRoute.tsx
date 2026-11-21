import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

export default function ProtectedRoute({
  children,
  allowIncompleteOnboarding = false,
}: {
  children: ReactNode;
  allowIncompleteOnboarding?: boolean;
}) {
  const location = useLocation();
  const token = localStorage.getItem("align_token");
  if (!token) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  const isOnboarded = localStorage.getItem("align_onboarded");
  if (isOnboarded === "false" && !allowIncompleteOnboarding && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}
