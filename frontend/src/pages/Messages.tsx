import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowLeft, LoaderCircle, MessageCircle, Send, Sparkles, User as UserIcon } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, Message } from "../lib/api";
import { SafeAvatar } from "../components/common/SafeImage";

type ConversationItem = {
  partner_id: number;
  partner_name: string;
  partner_avatar?: string | null;
  last_message: string;
  last_message_at: string;
  unread_count: number;
};

export default function Messages() {
  const [searchParams] = useSearchParams();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeRecipient, setActiveRecipient] = useState<number | null>(null);
  const [activeRecipientName, setActiveRecipientName] = useState<string>("Select a conversation");
  const [newText, setNewText] = useState("");
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [showMobileChat, setShowMobileChat] = useState(false);

  useEffect(() => {
    // Read logged-in user id
    api.me()
      .then((u) => setCurrentUserId(u.id))
      .catch(() => {});

    loadConversations();
  }, []);

  // Check URL params for starting a conversation with a specific user
  useEffect(() => {
    const paramUserId = searchParams.get("user_id");
    const paramName = searchParams.get("name");
    if (paramUserId) {
      const uid = parseInt(paramUserId, 10);
      if (!isNaN(uid)) {
        setActiveRecipient(uid);
        setActiveRecipientName(paramName ? decodeURIComponent(paramName) : `User #${uid}`);
        setShowMobileChat(true);
      }
    }
  }, [searchParams]);

  useEffect(() => {
    if (activeRecipient) {
      loadMessages(activeRecipient);
    } else {
      setMessages([]);
    }
  }, [activeRecipient]);

  async function loadConversations() {
    setLoadingConversations(true);
    try {
      const convs = await api.conversations();
      setConversations(convs);

      // If no active recipient from URL and we have conversations, auto-select the first one
      if (!searchParams.get("user_id") && convs.length > 0 && activeRecipient === null) {
        setActiveRecipient(convs[0].partner_id);
        setActiveRecipientName(convs[0].partner_name);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadMessages(partnerId: number) {
    setLoadingMessages(true);
    setError("");
    try {
      const data = await api.messages(partnerId);
      setMessages(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages.");
    } finally {
      setLoadingMessages(false);
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!newText.trim()) return;
    if (!activeRecipient) {
      alert("Please select a recipient first.");
      return;
    }
    setSending(true);
    try {
      const sent = await api.sendMessage({
        receiver_id: activeRecipient,
        content: newText.trim(),
      });
      setMessages((prev) => [sent, ...prev]);
      setNewText("");
      // Refresh conversations snippet
      api.conversations().then(setConversations).catch(() => {});
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to send message.");
    } finally {
      setSending(false);
    }
  }

  return (
    <AppShell title="Messages">
      <div style={{ maxWidth: "1080px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "20px" }}>
          <p className="eyebrow">Connections</p>
          <h1 className="page-title">Start with a conversation.</h1>
          <p className="lead" style={{ margin: 0 }}>
            Connect 1-on-1 with community peers, collaborators, and mentors.
          </p>
        </div>

        {error && <div className="error-box" style={{ marginBottom: "16px" }}>{error}</div>}

        {/* Messaging Container */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px 1fr",
            background: "var(--bg-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "18px",
            boxShadow: "0 8px 30px rgba(244, 182, 194, 0.25)",
            overflow: "hidden",
            minHeight: "560px",
            height: "calc(100vh - 280px)",
            maxHeight: "720px",
          }}
        >
          {/* Left Sidebar: Conversation List */}
          <div
            style={{
              borderRight: "1px solid var(--border-subtle)",
              background: "var(--bg-card)",
              display: "flex",
              flexDirection: "column",
              height: "100%",
            }}
          >
            <div
              style={{
                padding: "16px",
                borderBottom: "1px solid var(--border-subtle)",
                fontWeight: "700",
                fontSize: "15px",
                color: "var(--primary-text)",
                background: "var(--bg-card-hover)",
              }}
            >
              Conversations
            </div>

            <div style={{ flex: 1, overflowY: "auto" }}>
              {loadingConversations ? (
                <div style={{ textAlign: "center", padding: "30px 16px", color: "var(--secondary-text)" }}>
                  <LoaderCircle className="spin" size={20} style={{ color: "var(--accent-pink)", margin: "0 auto 6px auto" }} />
                  <span style={{ fontSize: "12px" }}>Loading chats...</span>
                </div>
              ) : conversations.length === 0 ? (
                <div style={{ textAlign: "center", padding: "40px 16px", color: "var(--secondary-text)" }}>
                  <MessageCircle size={32} style={{ color: "var(--border-subtle)", margin: "0 auto 10px auto" }} />
                  <p style={{ fontSize: "13px", fontWeight: "600", color: "var(--primary-text)", margin: "0 0 4px 0" }}>
                    No conversations yet
                  </p>
                  <p style={{ fontSize: "12px", margin: 0 }}>
                    Find peers on the People page to start a chat!
                  </p>
                </div>
              ) : (
                conversations.map((c) => {
                  const isSelected = activeRecipient === c.partner_id;
                  return (
                    <div
                      key={c.partner_id}
                      onClick={() => {
                        setActiveRecipient(c.partner_id);
                        setActiveRecipientName(c.partner_name);
                        setShowMobileChat(true);
                      }}
                      style={{
                        padding: "12px 16px",
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        cursor: "pointer",
                        borderBottom: "1px solid var(--border-subtle)",
                        background: isSelected ? "var(--bg-main)" : "transparent",
                        borderLeft: isSelected ? "4px solid var(--button-pink)" : "4px solid transparent",
                        transition: "background 0.15s ease",
                      }}
                    >
                      <div
                        style={{
                          width: "38px",
                          height: "38px",
                          borderRadius: "50%",
                          background: "var(--powder-pink)",
                          border: "1.5px solid var(--border-subtle)",
                          display: "grid",
                          placeItems: "center",
                          overflow: "hidden",
                          flexShrink: 0,
                        }}
                      >
                        <SafeAvatar
                          src={c.partner_avatar}
                          name={c.partner_name}
                          size={40}
                        />
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                          <span
                            style={{
                              fontSize: "13px",
                              fontWeight: isSelected ? "700" : "600",
                              color: "var(--primary-text)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              maxWidth: "140px",
                            }}
                          >
                            {c.partner_name}
                          </span>
                          <span style={{ fontSize: "10px", color: "var(--secondary-text)" }}>
                            {c.last_message_at ? new Date(c.last_message_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
                          </span>
                        </div>
                        <p
                          style={{
                            margin: 0,
                            fontSize: "12px",
                            color: "var(--secondary-text)",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {c.last_message || "No messages yet"}
                        </p>
                      </div>

                      {c.unread_count > 0 && (
                        <span
                          style={{
                            background: "var(--accent-pink)",
                            color: "#FFFFFF",
                            borderRadius: "100px",
                            fontSize: "10px",
                            fontWeight: "700",
                            padding: "2px 6px",
                            flexShrink: 0,
                          }}
                        >
                          {c.unread_count}
                        </span>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Chat Window */}
          <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg-card)" }}>
            {/* Chat Header */}
            <div
              style={{
                padding: "14px 20px",
                borderBottom: "1px solid var(--border-subtle)",
                background: "var(--bg-card-hover)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "38px",
                    height: "38px",
                    borderRadius: "50%",
                    background: "var(--powder-pink)",
                    border: "1.5px solid var(--border-subtle)",
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <UserIcon size={18} style={{ color: "var(--primary-text)" }} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: "15px", color: "var(--primary-text)", fontWeight: "700" }}>
                    {activeRecipient ? activeRecipientName : "ALIGN Chat"}
                  </h3>
                  <span style={{ fontSize: "12px", color: "var(--secondary-text)" }}>
                    {activeRecipient ? "Direct Message" : "Select a peer from the left sidebar to start chatting"}
                  </span>
                </div>
              </div>
            </div>

            {/* Messages Thread */}
            <div
              style={{
                flex: 1,
                padding: "20px",
                overflowY: "auto",
                display: "flex",
                flexDirection: "column-reverse",
                gap: "12px",
                background: "var(--bg-main)",
              }}
            >
              {loadingMessages ? (
                <div style={{ margin: "auto", textAlign: "center", color: "var(--secondary-text)" }}>
                  <LoaderCircle className="spin" size={28} style={{ color: "var(--accent-pink)", margin: "0 auto 8px auto" }} />
                  <p style={{ fontSize: "13px" }}>Loading messages...</p>
                </div>
              ) : !activeRecipient ? (
                <div style={{ margin: "auto", textAlign: "center", padding: "40px 16px" }}>
                  <MessageCircle size={44} style={{ color: "var(--border-subtle)", margin: "0 auto 12px auto" }} />
                  <h4 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>Select a Conversation</h4>
                  <p style={{ color: "var(--secondary-text)", fontSize: "13px", maxWidth: "300px", margin: "0 auto" }}>
                    Pick an existing conversation from the list or visit the People page to start a new chat.
                  </p>
                </div>
              ) : messages.length === 0 ? (
                <div style={{ margin: "auto", textAlign: "center", padding: "40px 16px" }}>
                  <MessageCircle size={40} style={{ color: "var(--accent-pink)", margin: "0 auto 12px auto" }} />
                  <h4 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>Start of Conversation</h4>
                  <p style={{ color: "var(--secondary-text)", fontSize: "13px", maxWidth: "320px", margin: "0 auto" }}>
                    Say hello to {activeRecipientName}! Break the ice with questions about shared interests or projects.
                  </p>
                </div>
              ) : (
                messages.map((m) => {
                  const isMine = currentUserId ? m.sender_id === currentUserId : false;

                  return (
                    <div
                      key={m.id}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: isMine ? "flex-end" : "flex-start",
                        maxWidth: "75%",
                        alignSelf: isMine ? "flex-end" : "flex-start",
                      }}
                    >
                      <span style={{ fontSize: "11px", color: "var(--secondary-text)", marginBottom: "3px", padding: "0 4px" }}>
                        {isMine ? "You" : m.sender_name || activeRecipientName}
                      </span>
                      <div
                        style={{
                          padding: "10px 16px",
                          borderRadius: isMine ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                          background: isMine ? "var(--button-pink)" : "#FFFFFF",
                          color: isMine ? "#FFFFFF" : "var(--primary-text)",
                          border: isMine ? "none" : "1px solid var(--border-subtle)",
                          fontSize: "14px",
                          lineHeight: "1.5",
                          boxShadow: "0 2px 8px rgba(244, 182, 194, 0.15)",
                          wordBreak: "break-word",
                        }}
                      >
                        {m.content}
                      </div>
                      <span style={{ fontSize: "10px", color: "var(--secondary-text)", marginTop: "3px", padding: "0 4px" }}>
                        {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  );
                })
              )}
            </div>

            {/* Input Bar */}
            <form
              onSubmit={handleSend}
              style={{
                padding: "14px 20px",
                borderTop: "1px solid var(--border-subtle)",
                background: "var(--bg-card)",
                display: "flex",
                gap: "10px",
                alignItems: "center",
              }}
            >
              <input
                type="text"
                disabled={!activeRecipient}
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                placeholder={activeRecipient ? `Message ${activeRecipientName}...` : "Select a conversation to type..."}
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  borderRadius: "12px",
                  border: "1.5px solid var(--border-subtle)",
                  background: "var(--bg-main)",
                  color: "var(--primary-text)",
                  fontSize: "14px",
                  outline: "none",
                }}
              />
              <button
                type="submit"
                disabled={sending || !newText.trim() || !activeRecipient}
                className="submit-button"
                style={{
                  margin: 0,
                  width: "auto",
                  padding: "12px 20px",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontWeight: "600",
                }}
              >
                {sending ? <LoaderCircle className="spin" size={15} /> : <Send size={15} />}
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
