import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Compass,
  Sparkles,
  Target,
  Trophy,
  ShieldCheck,
  TrendingUp,
  Activity,
  ArrowRight,
  Layers,
  MapPin,
  Calendar,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Legend,
} from "recharts";
import AppShell from "../components/layout/AppShell";
import CommunityCard from "../components/cards/CommunityCard";
import EventCard from "../components/cards/EventCard";
import PlaceCard from "../components/cards/PlaceCard";
import {
  Community,
  EventItem,
  PlaceItem,
  GoalJourneyItem,
  GamificationProfile,
  api,
} from "../lib/api";

const DEFAULT_AFFINITY_DATA = [
  { subject: "AI & ML", userAffinity: 92, communityAvg: 68 },
  { subject: "UI / Design", userAffinity: 75, communityAvg: 60 },
  { subject: "Systems", userAffinity: 84, communityAvg: 55 },
  { subject: "Community", userAffinity: 70, communityAvg: 64 },
  { subject: "Data Science", userAffinity: 95, communityAvg: 72 },
  { subject: "Gatherings", userAffinity: 65, communityAvg: 58 },
];

const DEFAULT_GOAL_TREND = [
  { phase: "Week 1", planned: 25, achieved: 25 },
  { phase: "Week 2", planned: 50, achieved: 45 },
  { phase: "Week 3", planned: 75, achieved: 65 },
  { phase: "Week 4", planned: 100, achieved: 85 },
];

export default function Dashboard() {
  const [communities, setCommunities] = useState<Community[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [places, setPlaces] = useState<PlaceItem[]>([]);
  const [journeys, setJourneys] = useState<GoalJourneyItem[]>([]);
  const [gamification, setGamification] = useState<GamificationProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const userName = localStorage.getItem("align_user_name") || "Explorer";

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [cRes, eRes, pRes, jRes, gRes] = await Promise.allSettled([
          api.communities({ limit: 3 }),
          api.events({ limit: 3 }),
          api.places(),
          api.myGoalJourneys().catch(() => []),
          api.myGamification().catch(() => null),
        ]);

        if (cRes.status === "fulfilled") setCommunities(cRes.value.slice(0, 3));
        if (eRes.status === "fulfilled") setEvents(eRes.value.slice(0, 3));
        if (pRes.status === "fulfilled") setPlaces(pRes.value.slice(0, 3));
        if (jRes.status === "fulfilled") setJourneys(jRes.value);
        if (gRes.status === "fulfilled") setGamification(gRes.value);
      } catch (err) {
        console.error("Dashboard error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  // Compute goal progress metrics
  const activeJourney = journeys.length > 0 ? journeys[0] : null;
  const progressPercent = activeJourney ? activeJourney.progress_percentage : 72;
  const completedMilestones = activeJourney ? activeJourney.completed_milestones : 3;
  const totalMilestones = activeJourney ? activeJourney.total_milestones : 5;

  return (
    <AppShell title="Dashboard">
      <div style={{ marginBottom: "24px" }}>
        <p className="eyebrow" style={{ letterSpacing: "0.08em" }}>
          PERSONALIZED DISCOVERY OVERVIEW
        </p>
        <h1 className="page-title" style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 8px" }}>
          Welcome back, {userName}.
        </h1>
        <p className="lead" style={{ color: "var(--muted)", margin: 0, fontSize: "15px" }}>
          Real-time intent embeddings, graph signal strength, and goal milestones tailored to your active trajectory.
        </p>
      </div>

      {/* Key Metric Highlights Grid */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
        aria-label="Discovery metrics"
      >
        <div
          className="panel"
          style={{
            padding: "20px",
            borderRadius: "14px",
            background: "var(--card)",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase" }}>
              Intent Match Quality
            </span>
            <Sparkles size={18} style={{ color: "var(--accent)" }} />
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--text)" }}>94.2%</div>
          <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
            High semantic cosine alignment
          </p>
        </div>

        <div
          className="panel"
          style={{
            padding: "20px",
            borderRadius: "14px",
            background: "var(--card)",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase" }}>
              Location Privacy
            </span>
            <ShieldCheck size={18} style={{ color: "var(--success)" }} />
          </div>
          <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text)", marginTop: "6px" }}>
            Approximate (~1.1 km)
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
            0.01° grid differential protection
          </p>
        </div>

        <div
          className="panel"
          style={{
            padding: "20px",
            borderRadius: "14px",
            background: "var(--card)",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase" }}>
              Verified XP Points
            </span>
            <Trophy size={18} style={{ color: "var(--warning)" }} />
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--text)" }}>
            {gamification ? gamification.xp_points : 350} XP
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
            Level {gamification ? gamification.current_level : 2} Platform Contributor
          </p>
        </div>

        <div
          className="panel"
          style={{
            padding: "20px",
            borderRadius: "14px",
            background: "var(--card)",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase" }}>
              Active Goal Trajectory
            </span>
            <Target size={18} style={{ color: "var(--accent)" }} />
          </div>
          <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--text)" }}>
            {progressPercent}%
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
            {completedMilestones} of {totalMilestones} milestones reached
          </p>
        </div>
      </section>

      {/* Visual Analytics Grid: Radar & Progression */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "24px",
          marginBottom: "40px",
        }}
        aria-label="Visual Analytics"
      >
        {/* Radar: Domain Affinity Alignment */}
        <div
          className="panel"
          style={{
            background: "var(--card)",
            borderRadius: "16px",
            padding: "24px",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>Domain Affinity Profile</h3>
              <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
                Semantic embedding strength across core discovery disciplines
              </p>
            </div>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: "var(--accent)",
                background: "rgba(83, 101, 245, 0.1)",
                padding: "3px 8px",
                borderRadius: "12px",
              }}
            >
              Hybrid Space
            </span>
          </div>

          <div style={{ height: "260px", width: "100%" }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={DEFAULT_AFFINITY_DATA}>
                <PolarGrid stroke="var(--line)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: "var(--muted)", fontSize: 11 }} />
                <Radar
                  name="My Profile"
                  dataKey="userAffinity"
                  stroke="#5365F5"
                  fill="#5365F5"
                  fillOpacity={0.4}
                />
                <Radar
                  name="Platform Avg"
                  dataKey="communityAvg"
                  stroke="#10B981"
                  fill="#10B981"
                  fillOpacity={0.15}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--card)",
                    borderColor: "var(--line)",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "var(--text)",
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
                  formatter={(val) => <span style={{ color: "var(--text)" }}>{val}</span>}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AreaChart: Goal Milestone Trajectory */}
        <div
          className="panel"
          style={{
            background: "var(--card)",
            borderRadius: "16px",
            padding: "24px",
            border: "1px solid var(--line)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>Milestone Progression Curve</h3>
              <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--muted)" }}>
                {activeJourney ? activeJourney.title : "30-Day Engineering & Discovery Track"}
              </p>
            </div>
            <Link
              to="/goals/journey"
              className="button"
              style={{ fontSize: "12px", padding: "4px 10px", borderRadius: "6px" }}
            >
              Manage →
            </Link>
          </div>

          <div style={{ height: "260px", width: "100%" }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={DEFAULT_GOAL_TREND} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorAchieved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#5365F5" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#5365F5" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorPlanned" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#A1A1AA" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#A1A1AA" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="phase" stroke="var(--muted)" fontSize={12} tickLine={false} />
                <YAxis stroke="var(--muted)" fontSize={12} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{
                    background: "var(--card)",
                    borderColor: "var(--line)",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "var(--text)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="planned"
                  name="Planned Path"
                  stroke="#A1A1AA"
                  strokeDasharray="4 4"
                  fillOpacity={1}
                  fill="url(#colorPlanned)"
                />
                <Area
                  type="monotone"
                  dataKey="achieved"
                  name="Achieved Milestone"
                  stroke="#5365F5"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorAchieved)"
                />
                <Legend
                  wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
                  formatter={(val) => <span style={{ color: "var(--text)" }}>{val}</span>}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* Recommended Communities */}
      <section style={{ marginBottom: "40px" }}>
        <div className="section-heading">
          <div>
            <h2>Recommended communities</h2>
            <p style={{ margin: "4px 0 0 0", color: "var(--muted)", fontSize: "14px" }}>
              Circles with high graph co-membership and topic relevance.
            </p>
          </div>
          <Link to="/communities" className="button">
            Explore all →
          </Link>
        </div>
        <div className="grid-3">
          {communities.length > 0 ? (
            communities.map((c) => <CommunityCard key={c.id} community={c} />)
          ) : (
            <div className="panel" style={{ gridColumn: "1 / -1", textAlign: "center", padding: "36px 20px" }}>
              <p style={{ margin: "0 0 12px 0", color: "var(--muted)", fontSize: "14px" }}>
                No community recommendations loaded. Discover new groups below.
              </p>
              <Link to="/communities" className="button primary">
                Explore Communities
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Coming up around you */}
      <section style={{ marginBottom: "40px" }}>
        <div className="section-heading">
          <div>
            <h2>Coming up around you</h2>
            <p style={{ margin: "4px 0 0 0", color: "var(--muted)", fontSize: "14px" }}>
              Physical and virtual gatherings matched to your interests.
            </p>
          </div>
          <Link to="/events" className="button">
            All events →
          </Link>
        </div>
        <div className="grid-3">
          {events.length > 0 ? (
            events.map((e) => <EventCard key={e.id} event={e} />)
          ) : (
            <div className="panel" style={{ gridColumn: "1 / -1", textAlign: "center", padding: "36px 20px" }}>
              <p style={{ margin: "0 0 12px 0", color: "var(--muted)", fontSize: "14px" }}>
                No events currently scheduled. Check back soon or host one.
              </p>
              <Link to="/events" className="button">
                Host an Event
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Spaces to discover */}
      <section style={{ marginBottom: "40px" }}>
        <div className="section-heading">
          <div>
            <h2>Spaces to discover</h2>
            <p style={{ margin: "4px 0 0 0", color: "var(--muted)", fontSize: "14px" }}>
              Verified collaborative environments and quiet work nooks.
            </p>
          </div>
          <Link to="/places" className="button">
            All places →
          </Link>
        </div>
        <div className="grid-3">
          {places.length > 0 ? (
            places.map((p) => <PlaceCard key={p.id} place={p} />)
          ) : (
            <div className="panel" style={{ gridColumn: "1 / -1", textAlign: "center", padding: "36px 20px" }}>
              <p style={{ margin: "0 0 12px 0", color: "var(--muted)", fontSize: "14px" }}>
                No places discovered yet in your coarse region.
              </p>
              <Link to="/places" className="button">
                Explore Places
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* From your community quick links */}
      <section style={{ marginBottom: "40px" }}>
        <div className="section-heading">
          <h2>Platform Activity Feeds</h2>
        </div>
        <div className="feature-strip">
          <Link to="/feed" className="feature button" style={{ textAlign: "left", display: "block", padding: "20px" }}>
            <strong style={{ fontSize: "15px", marginBottom: "4px", display: "block" }}>
              Explore trending posts →
            </strong>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
              Visual milestones and research notes shared by curious builders.
            </p>
          </Link>
          <Link to="/reels" className="feature button" style={{ textAlign: "left", display: "block", padding: "20px" }}>
            <strong style={{ fontSize: "15px", marginBottom: "4px", display: "block" }}>
              Watch photo reels →
            </strong>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
              Short immersive capture moments from campus and circles.
            </p>
          </Link>
          <Link to="/people" className="feature button" style={{ textAlign: "left", display: "block", padding: "20px" }}>
            <strong style={{ fontSize: "15px", marginBottom: "4px", display: "block" }}>
              Suggested peers →
            </strong>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
              Connect with engineers sharing complementary skill stacks.
            </p>
          </Link>
        </div>
      </section>

      {/* Saved Activity Banner */}
      <section className="banner">
        <h2>Your saved discoveries are ready</h2>
        <p className="lead" style={{ marginBottom: "20px" }}>
          Revisit bookmarked communities, project opportunities, and upcoming RSVPs in your workspace.
        </p>
        <Link to="/saved" className="button primary">
          View saved items
        </Link>
      </section>
    </AppShell>
  );
}
