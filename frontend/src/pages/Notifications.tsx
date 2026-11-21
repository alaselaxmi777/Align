import { useEffect, useState } from "react";
import {
  Bell,
  CalendarDays,
  Check,
  Heart,
  MessageCircle,
  Sparkles,
  UserPlus,
  Users,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, Notification } from "../lib/api";

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [markedAll, setMarkedAll] = useState(false);

  useEffect(() => {
    async function loadNotifications() {
      try {
        const data = await api.notifications();
        setNotifications(data);
      } catch (err) {
        console.error("Failed to load notifications:", err);
      } finally {
        setLoading(false);
      }
    }
    loadNotifications();
  }, []);

  async function handleMarkRead(id: number) {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error(err);
    }
  }

  function handleMarkAllAsRead() {
    notifications.forEach((n) => {
      if (!n.is_read) handleMarkRead(n.id);
    });
    setMarkedAll(true);
  }

  return (
    <AppShell title="Notifications">
      <p className="eyebrow">Stay in the loop</p>
      <h1 className="page-title">Notifications</h1>

      <div className="panel" style={{ marginTop: "20px", opacity: markedAll ? 0.75 : 1, transition: "opacity .3s ease" }}>
        {notifications.length > 0 ? (
          notifications.map((n) => (
            <div
              key={n.id}
              className="list-row"
              style={{
                background: n.is_read ? "transparent" : "var(--sub)",
                cursor: "pointer",
              }}
              onClick={() => handleMarkRead(n.id)}
            >
              <Bell size={20} />
              <div>
                <strong>{n.title}</strong>
                <p>{n.message}</p>
              </div>
              <time>
                {new Date(n.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })}
              </time>
            </div>
          ))
        ) : (
          <div style={{ textAlign: "center", padding: "48px 20px", color: "var(--muted)" }}>
            <Bell size={32} style={{ margin: "0 auto 12px auto", opacity: 0.6 }} />
            <h3 style={{ margin: "0 0 6px 0", color: "var(--text)" }}>All caught up</h3>
            <p style={{ margin: 0, fontSize: "14px" }}>
              No notifications yet. Activity from your communities, connections, and posts will appear here.
            </p>
          </div>
        )}
      </div>

      <div className="actions" style={{ marginTop: "20px" }}>
        <button
          type="button"
          className="button"
          onClick={handleMarkAllAsRead}
          disabled={markedAll}
        >
          {markedAll ? "All marked as read ✓" : "Mark all as read"}
        </button>
      </div>
    </AppShell>
  );
}
