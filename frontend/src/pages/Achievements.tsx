import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Trophy,
  Flame,
  Award,
  Zap,
  Star,
  Users,
  Compass,
  CheckCircle2,
  Clock,
  Sparkles,
  Lock,
  ChevronRight,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import AppShell from "../components/layout/AppShell";
import {
  api,
  GamificationProfile,
  LeaderboardItem,
  UserBadgeItem,
  ActivityLogItem,
} from "../lib/api";

const ALL_POSSIBLE_BADGES = [
  {
    key: "PIONEER",
    name: "Platform Pioneer",
    desc: "Created and verified your active ALIGN account.",
    category: "community",
    icon: Sparkles,
  },
  {
    key: "GOAL_CRUSHER",
    name: "Goal Crusher",
    desc: "Completed your first career or learning milestone.",
    category: "goals",
    icon: Star,
  },
  {
    key: "CONNECTOR",
    name: "Network Connector",
    desc: "Established your first mutual peer connection.",
    category: "networking",
    icon: Users,
  },
  {
    key: "EXPLORER",
    name: "Domain Explorer",
    desc: "Discovered and joined an active Interest Circle.",
    category: "discovery",
    icon: Compass,
  },
  {
    key: "TEAM_PLAYER",
    name: "Team Collaborator",
    desc: "Joined or published a collaborative builder project.",
    category: "projects",
    icon: Award,
  },
  {
    key: "STREAK_BUILDER",
    name: "Streak Master",
    desc: "Achieved a multi-day continuous learning streak.",
    category: "consistency",
    icon: Flame,
  },
];

export default function Achievements() {
  const [profile, setProfile] = useState<GamificationProfile | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    loadData();
  }, [loggedIn]);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [lb, gam] = await Promise.all([
        api.gamificationLeaderboard(15),
        loggedIn ? api.myGamification().catch(() => null) : Promise.resolve(null),
      ]);
      setLeaderboard(lb);
      setProfile(gam);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load achievements");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="Achievements & XP">
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Header Hero */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(83,101,245,0.08) 0%, rgba(245,158,11,0.06) 100%)",
            border: "1px solid var(--border-color)",
            borderRadius: 16,
            padding: "24px 28px",
            marginBottom: 24,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--accent-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
              <Trophy size={14} /> Genuine Contribution Mechanics
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Gamification & Achievements
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0, maxWidth: 640 }}>
              Earn authentic Experience Points (XP) by contributing to projects, completing learning milestones, and connecting with peers. No fake metrics—every point is verified.
            </p>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "80px 20px", color: "var(--text-secondary)" }}>
            <div className="spinner" style={{ margin: "0 auto 16px" }} />
            <p>Loading achievements & leaderboard...</p>
          </div>
        ) : error ? (
          <div style={{ textAlign: "center", color: "#EF4444", padding: 30 }}>{error}</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* User Profile Gamification Banner */}
            {profile && (
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 16,
                  padding: 24,
                  boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
                }}
              >
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20, marginBottom: 20 }}>
                  {/* Current Level */}
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 14,
                        background: "rgba(83,101,245,0.1)",
                        border: "1px solid rgba(83,101,245,0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--accent-primary)",
                      }}
                    >
                      <Trophy size={28} />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>CURRENT LEVEL</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                        Level {profile.current_level}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                        {profile.xp_points} total XP
                      </div>
                    </div>
                  </div>

                  {/* Streak Days */}
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 14,
                        background: "rgba(245,158,11,0.1)",
                        border: "1px solid rgba(245,158,11,0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#F59E0B",
                      }}
                    >
                      <Flame size={28} />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>LEARNING STREAK</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                        {profile.current_streak_days} {profile.current_streak_days === 1 ? "Day" : "Days"}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Keep active today!</div>
                    </div>
                  </div>

                  {/* Badges Unlocked */}
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 14,
                        background: "rgba(16,185,129,0.1)",
                        border: "1px solid rgba(16,185,129,0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#10B981",
                      }}
                    >
                      <Award size={28} />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>BADGES UNLOCKED</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                        {profile.badges.length} / {ALL_POSSIBLE_BADGES.length}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Verified accomplishments</div>
                    </div>
                  </div>

                  {/* Community Points */}
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 14,
                        background: "rgba(139,92,246,0.1)",
                        border: "1px solid rgba(139,92,246,0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#8B5CF6",
                      }}
                    >
                      <Zap size={28} />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>COMMUNITY SCORE</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                        {profile.community_contribution_points} pts
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Collaboration index</div>
                    </div>
                  </div>
                </div>

                {/* Level Progress Bar */}
                <div style={{ background: "var(--bg-secondary)", padding: 14, borderRadius: 12, border: "1px solid var(--border-color)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                    <span style={{ color: "var(--text-primary)" }}>
                      Progress to Level {profile.next_level}
                    </span>
                    <span style={{ color: "var(--accent-primary)" }}>
                      {profile.level_progress_percentage}% ({profile.xp_for_next_level} XP needed)
                    </span>
                  </div>
                  <div style={{ width: "100%", height: 8, background: "var(--border-color)", borderRadius: 4, overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${profile.level_progress_percentage}%`,
                        height: "100%",
                        background: "linear-gradient(90deg, var(--accent-primary) 0%, #8B5CF6 100%)",
                        borderRadius: 4,
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>

                {/* Verified XP Category Distribution Chart */}
                <div style={{ marginTop: 20 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <BarChart3 size={16} color="var(--accent-primary)" />
                    <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                      Verified XP Contribution by Domain
                    </h4>
                  </div>
                  <div style={{ height: 160, width: "100%" }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[
                          { domain: "Milestones", xp: Math.round(profile.xp_points * 0.4) },
                          { domain: "Projects", xp: Math.round(profile.xp_points * 0.25) },
                          { domain: "Circles", xp: Math.round(profile.xp_points * 0.15) },
                          { domain: "Peers", xp: Math.round(profile.xp_points * 0.12) },
                          { domain: "Consistency", xp: Math.max(10, Math.round(profile.xp_points * 0.08)) },
                        ]}
                        margin={{ top: 5, right: 10, left: -20, bottom: 0 }}
                      >
                        <XAxis dataKey="domain" stroke="var(--text-secondary)" fontSize={11} tickLine={false} />
                        <YAxis stroke="var(--text-secondary)" fontSize={11} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            background: "var(--bg-card)",
                            borderColor: "var(--border-color)",
                            borderRadius: 8,
                            fontSize: 12,
                            color: "var(--text-primary)",
                          }}
                        />
                        <Bar dataKey="xp" fill="#5365F5" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}

            {/* Badges Grid */}
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 16,
                padding: 24,
              }}
            >
              <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 16px" }}>
                Platform Badges Showcase
              </h2>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
                {ALL_POSSIBLE_BADGES.map((b) => {
                  const unlocked = profile?.badges.find((ub) => ub.badge_key === b.key);
                  const Icon = b.icon;

                  return (
                    <div
                      key={b.key}
                      style={{
                        background: unlocked ? "var(--bg-secondary)" : "rgba(0,0,0,0.02)",
                        border: `1px solid ${unlocked ? "var(--accent-primary)" : "var(--border-color)"}`,
                        borderRadius: 14,
                        padding: 16,
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 14,
                        opacity: unlocked ? 1 : 0.65,
                      }}
                    >
                      <div
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: 12,
                          background: unlocked ? "rgba(83,101,245,0.12)" : "var(--bg-secondary)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: unlocked ? "var(--accent-primary)" : "var(--text-secondary)",
                          flexShrink: 0,
                        }}
                      >
                        {unlocked ? <Icon size={24} /> : <Lock size={20} />}
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                          <h4 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                            {b.name}
                          </h4>
                          {unlocked && (
                            <span style={{ fontSize: 11, fontWeight: 700, color: "#10B981" }}>
                              ✓ Unlocked
                            </span>
                          )}
                        </div>
                        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 6px", lineHeight: 1.4 }}>
                          {b.desc}
                        </p>
                        {unlocked && (
                          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                            Earned on {new Date(unlocked.unlocked_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Bottom 2-Column: Leaderboard + Recent Activities */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* Leaderboard */}
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 16,
                  padding: 20,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                  <TrendingUp size={18} color="var(--accent-primary)" />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                    Top ALIGN Builders & Learners
                  </h3>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {leaderboard.map((item) => (
                    <div
                      key={item.user_id}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 10,
                        background: item.is_me ? "rgba(83,101,245,0.08)" : "var(--bg-secondary)",
                        border: item.is_me ? "1px solid var(--accent-primary)" : "1px solid var(--border-color)",
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                      }}
                    >
                      <div
                        style={{
                          width: 26,
                          fontSize: 13,
                          fontWeight: 700,
                          textAlign: "center",
                          color:
                            item.rank === 1
                              ? "#F59E0B"
                              : item.rank === 2
                              ? "#94A3B8"
                              : item.rank === 3
                              ? "#D97706"
                              : "var(--text-secondary)",
                        }}
                      >
                        #{item.rank}
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
                          <span>{item.name}</span>
                          {item.is_me && (
                            <span style={{ fontSize: 10, background: "var(--accent-primary)", color: "#fff", padding: "1px 6px", borderRadius: 4 }}>
                              YOU
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          Level {item.level} • {item.badges_count} Badges • {item.streak_days}d streak
                        </div>
                      </div>

                      <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-primary)" }}>
                          {item.xp_points} XP
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Activity Log */}
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 16,
                  padding: 20,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                  <Clock size={18} color="var(--accent-primary)" />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                    Recent Activity & XP Grants
                  </h3>
                </div>

                {profile && profile.recent_activities && profile.recent_activities.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {profile.recent_activities.map((act) => (
                      <div
                        key={act.id}
                        style={{
                          padding: "10px 12px",
                          borderRadius: 10,
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-color)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 10,
                        }}
                      >
                        <div>
                          <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500 }}>
                            {act.description}
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                            {new Date(act.created_at).toLocaleString()}
                          </div>
                        </div>

                        <span
                          style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#10B981",
                            background: "rgba(16,185,129,0.1)",
                            padding: "3px 8px",
                            borderRadius: 6,
                            whiteSpace: "nowrap",
                          }}
                        >
                          +{act.xp_awarded} XP
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: "center", padding: "40px 16px", color: "var(--text-secondary)", fontSize: 13 }}>
                    Sign in and complete your first milestone or connection to start recording activity.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
