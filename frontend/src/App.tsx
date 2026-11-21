import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ToastProvider } from "./components/common/ToastContext";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Discover from "./pages/Discover";
import People from "./pages/People";
import Communities from "./pages/Communities";
import CommunityDetail from "./pages/CommunityDetail";
import Events from "./pages/Events";
import Activities from "./pages/Activities";
import Places from "./pages/Places";
import Feed from "./pages/Feed";
import Reels from "./pages/Reels";
import Messages from "./pages/Messages";
import Notifications from "./pages/Notifications";
import Saved from "./pages/Saved";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import Auth from "./pages/Auth";
import Onboarding from "./pages/Onboarding";
import SkillsHobbies from "./pages/SkillsHobbies";
import GoalsInterests from "./pages/GoalsInterests";
import Admin from "./pages/Admin";
import DataHealth from "./pages/DataHealth";
import ProtectedRoute from "./components/ProtectedRoute";
import Assistant from "./pages/Assistant";
import Circles from "./pages/Circles";
import CircleDetail from "./pages/CircleDetail";
import GoalJourney from "./pages/GoalJourney";
import DiscoveryMap from "./pages/DiscoveryMap";
import Achievements from "./pages/Achievements";
import Projects from "./pages/Projects";
import ProjectDetail from "./pages/ProjectDetail";
import Opportunities from "./pages/Opportunities";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import TermsOfService from "./pages/TermsOfService";

export default function App() {
  const location = useLocation();

  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "ALIGN — Find Your People. Discover Your World.",
      "/login": "Sign In — ALIGN",
      "/register": "Create Account — ALIGN",
      "/privacy": "Privacy Policy — ALIGN",
      "/terms": "Terms of Service — ALIGN",
      "/onboarding": "Welcome Setup — ALIGN",
      "/feed": "Community Feed — ALIGN",
      "/reels": "Reels & Clips — ALIGN",
      "/discover": "Discover Experiences — ALIGN",
      "/people": "Peer Discovery — ALIGN",
      "/messages": "Direct Messages — ALIGN",
      "/notifications": "Notifications — ALIGN",
      "/saved": "Saved Bookmarks — ALIGN",
      "/profile": "My Profile — ALIGN",
      "/settings": "Settings & Security — ALIGN",
      "/communities": "Communities — ALIGN",
      "/events": "Events & Meetups — ALIGN",
      "/assistant": "AI Assistant — ALIGN",
      "/circles": "Interest Circles — ALIGN",
      "/goals/journey": "Goal Journey — ALIGN",
      "/map": "Discovery Map — ALIGN",
      "/achievements": "Achievements — ALIGN",
      "/projects": "Projects & Collaborations — ALIGN",
      "/opportunities": "Opportunities — ALIGN",
    };

    const exact = titles[location.pathname];
    if (exact) {
      document.title = exact;
    } else if (location.pathname.startsWith("/profile/")) {
      document.title = "User Profile — ALIGN";
    } else if (location.pathname.startsWith("/communities/")) {
      document.title = "Community — ALIGN";
    } else if (location.pathname.startsWith("/circles/")) {
      document.title = "Circle — ALIGN";
    } else if (location.pathname.startsWith("/projects/")) {
      document.title = "Project — ALIGN";
    } else {
      document.title = "ALIGN — Find Your People. Discover Your World.";
    }
  }, [location.pathname]);

  return (
    <ToastProvider>
      <Routes>
      {/* Public Pages */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Auth mode="login" />} />
      <Route path="/register" element={<Auth mode="register" />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />
      <Route path="/terms" element={<TermsOfService />} />

      {/* Onboarding */}
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute allowIncompleteOnboarding>
            <Onboarding />
          </ProtectedRoute>
        }
      />

      {/* Core Discovery & Social Protected Routes */}
      <Route
        path="/feed"
        element={
          <ProtectedRoute>
            <Feed />
          </ProtectedRoute>
        }
      />
      <Route path="/posts" element={<Navigate to="/feed" replace />} />
      <Route
        path="/reels"
        element={
          <ProtectedRoute>
            <Reels />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/discover"
        element={
          <ProtectedRoute>
            <Discover />
          </ProtectedRoute>
        }
      />
      <Route path="/explore" element={<Navigate to="/discover" replace />} />
      <Route
        path="/people"
        element={
          <ProtectedRoute>
            <People />
          </ProtectedRoute>
        }
      />
      <Route
        path="/skills-hobbies"
        element={
          <ProtectedRoute>
            <SkillsHobbies />
          </ProtectedRoute>
        }
      />
      <Route
        path="/goals-interests"
        element={
          <ProtectedRoute>
            <GoalsInterests />
          </ProtectedRoute>
        }
      />
      <Route
        path="/communities"
        element={
          <ProtectedRoute>
            <Communities />
          </ProtectedRoute>
        }
      />
      <Route
        path="/communities/:id"
        element={
          <ProtectedRoute>
            <CommunityDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/events"
        element={
          <ProtectedRoute>
            <Events />
          </ProtectedRoute>
        }
      />
      <Route
        path="/activities"
        element={
          <ProtectedRoute>
            <Activities />
          </ProtectedRoute>
        }
      />
      <Route
        path="/places"
        element={
          <ProtectedRoute>
            <Places />
          </ProtectedRoute>
        }
      />

      {/* Next-Gen Platform Features */}
      <Route
        path="/assistant"
        element={
          <ProtectedRoute>
            <Assistant />
          </ProtectedRoute>
        }
      />
      <Route
        path="/circles"
        element={
          <ProtectedRoute>
            <Circles />
          </ProtectedRoute>
        }
      />
      <Route
        path="/circles/:id"
        element={
          <ProtectedRoute>
            <CircleDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/goals/journey"
        element={
          <ProtectedRoute>
            <GoalJourney />
          </ProtectedRoute>
        }
      />
      <Route
        path="/map"
        element={
          <ProtectedRoute>
            <DiscoveryMap />
          </ProtectedRoute>
        }
      />
      <Route
        path="/achievements"
        element={
          <ProtectedRoute>
            <Achievements />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <Projects />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <ProjectDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/opportunities"
        element={
          <ProtectedRoute>
            <Opportunities />
          </ProtectedRoute>
        }
      />

      {/* Personal & Account Management Protected Routes */}
      <Route
        path="/messages"
        element={
          <ProtectedRoute>
            <Messages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <Notifications />
          </ProtectedRoute>
        }
      />
      <Route
        path="/saved"
        element={
          <ProtectedRoute>
            <Saved />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile/:id"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <Admin />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/data-health"
        element={
          <ProtectedRoute>
            <DataHealth />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </ToastProvider>
  );
}
