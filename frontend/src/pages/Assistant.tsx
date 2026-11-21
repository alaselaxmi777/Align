import { FormEvent, useEffect, useRef, useState } from "react";
import MarkdownView from "../components/common/MarkdownView";
import {
  Bot,
  Brain,
  Calendar,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Compass,
  Copy,
  ExternalLink,
  Flame,
  History,
  Layers,
  MapPin,
  MessageSquare,
  MoreVertical,
  Pin,
  PinOff,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  Share2,
  Shield,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  User as UserIcon,
  X,
  Archive,
  ArchiveRestore,
  Edit2,
  Bookmark,
  BookmarkCheck,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import {
  api,
  AssistantCard,
  AssistantCitation,
  AssistantConversationItem,
  AssistantMemoryItem,
  AssistantProposedMemory,
  AssistantSettingsItem,
} from "../lib/api";

const PRESET_PROMPTS = [
  "Find people interested in AI near me",
  "Recommend communities for learning programming",
  "Find upcoming technology events",
  "Help me achieve my career goals",
  "Discover hackathons and internships",
  "Find coworking spaces and innovation labs",
];

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  action_cards?: AssistantCard[];
  citations?: AssistantCitation[];
  suggested_prompts?: string[];
  proposed_memories?: AssistantProposedMemory[];
  created_at: string;
}

export default function Assistant() {
  const [conversations, setConversations] = useState<AssistantConversationItem[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<number | undefined>(undefined);
  const [filterType, setFilterType] = useState<"active" | "pinned" | "archived">("active");
  const [searchQuery, setSearchQuery] = useState("");
  
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      id: "init",
      role: "assistant",
      content:
        "Welcome to your **ALIGN Personal Intelligence Assistant**! I am connected to real platform data across verified members, learning communities, hackathons, and physical third places.\n\nHow can I help accelerate your projects or career today?",
      suggested_prompts: PRESET_PROMPTS,
      created_at: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Rename session inline state
  const [editingConvId, setEditingConvId] = useState<number | null>(null);
  const [editTitleInput, setEditTitleInput] = useState("");

  // Memory panel state
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [memories, setMemories] = useState<AssistantMemoryItem[]>([]);
  const [memorySettings, setMemorySettings] = useState<AssistantSettingsItem | null>(null);
  const [loadingMemories, setLoadingMemories] = useState(false);

  // Saved recommendations state
  const [savedRecMap, setSavedRecMap] = useState<Record<string, boolean>>({});
  const [feedbackMap, setFeedbackMap] = useState<Record<string, "useful" | "not_useful">>({});

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (loggedIn) {
      loadConversations();
      loadSettings();
    }
  }, [filterType, searchQuery]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  async function loadConversations() {
    try {
      const data = await api.assistantConversations(filterType, searchQuery.trim());
      setConversations(data);
    } catch {
      // unauthenticated or empty
    }
  }

  async function loadSettings() {
    try {
      const s = await api.assistantSettings();
      setMemorySettings(s);
    } catch {
      // not logged in
    }
  }

  async function loadMemories() {
    setLoadingMemories(true);
    try {
      const mems = await api.assistantMemories("all");
      setMemories(mems);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMemories(false);
    }
  }

  async function loadHistory(convId: number) {
    setSelectedConvId(convId);
    try {
      const hist = await api.assistantHistory(convId);
      setMessages(
        hist.map((m) => ({
          id: String(m.id),
          role: m.role as "user" | "assistant",
          content: m.content,
          action_cards: m.action_cards,
          citations: m.citations,
          suggested_prompts: m.suggested_followups,
          created_at: m.created_at,
        }))
      );
    } catch (err) {
      alert("Failed to load conversation history");
    }
  }

  function startNewConversation() {
    if (isStreaming && abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
    setSelectedConvId(undefined);
    setMessages([
      {
        id: String(Date.now()),
        role: "assistant",
        content: "Starting a fresh personal intelligence session. What would you like to explore or build?",
        suggested_prompts: PRESET_PROMPTS,
        created_at: new Date().toISOString(),
      },
    ]);
  }

  async function handleTogglePin(conv: AssistantConversationItem) {
    try {
      await api.updateAssistantConversation(conv.id, { pinned: !conv.pinned });
      loadConversations();
    } catch (err) {
      alert("Failed to update pin status");
    }
  }

  async function handleToggleArchive(conv: AssistantConversationItem) {
    try {
      await api.updateAssistantConversation(conv.id, { archived: !conv.archived });
      loadConversations();
    } catch (err) {
      alert("Failed to update archive status");
    }
  }

  async function handleSaveRename(convId: number) {
    if (!editTitleInput.trim()) return;
    try {
      await api.updateAssistantConversation(convId, { title: editTitleInput.trim() });
      setEditingConvId(null);
      loadConversations();
    } catch (err) {
      alert("Failed to rename conversation");
    }
  }

  async function handleDeleteConv(convId: number) {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await api.deleteAssistantConversation(convId);
      if (selectedConvId === convId) {
        startNewConversation();
      }
      loadConversations();
    } catch (err) {
      alert("Failed to delete conversation");
    }
  }

  function handleStopGeneration() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }

  async function handleSend(textToSend?: string) {
    const text = (textToSend || input).trim();
    if (!text || isStreaming) return;

    if (!loggedIn) {
      navigate("/login");
      return;
    }

    setInput("");
    const userMsgId = String(Date.now());
    const userMsg: ChatMsg = {
      id: userMsgId,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    const assistantMsgId = String(Date.now() + 1);
    const initialAssistantMsg: ChatMsg = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      action_cards: [],
      citations: [],
      suggested_prompts: [],
      proposed_memories: [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await api.assistantChatStream(
        text,
        selectedConvId,
        (eventName, data) => {
          if (eventName === "session") {
            if (data.conversation_id) {
              setSelectedConvId(data.conversation_id);
              loadConversations();
            }
          } else if (eventName === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: m.content + (data.token || "") }
                  : m
              )
            );
          } else if (eventName === "action_cards") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, action_cards: data.cards } : m
              )
            );
          } else if (eventName === "proposed_memory") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      proposed_memories: [...(m.proposed_memories || []), data],
                    }
                  : m
              )
            );
          } else if (eventName === "followups") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, suggested_prompts: data.prompts } : m
              )
            );
          }
        },
        controller.signal
      );
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content:
                    m.content ||
                    "I encountered an error connecting to ALIGN's discovery services. Please verify your connection.",
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
      loadConversations();
    }
  }

  async function handleRegenerate() {
    if (!selectedConvId || isStreaming) return;
    setIsStreaming(true);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await api.regenerateAssistantTurn(
        selectedConvId,
        (eventName, data) => {
          if (eventName === "token") {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last && last.role === "assistant") {
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: last.content + (data.token || "") },
                ];
              }
              return prev;
            });
          } else if (eventName === "action_cards") {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last && last.role === "assistant") {
                return [...prev.slice(0, -1), { ...last, action_cards: data.cards }];
              }
              return prev;
            });
          }
        },
        controller.signal
      );
    } catch (err) {
      console.error("Regenerate failed", err);
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }

  async function handleMemoryAction(memId: number, status: "approved" | "rejected") {
    try {
      await api.updateAssistantMemory(memId, { status });
      // Update local message proposed_memories
      setMessages((prev) =>
        prev.map((m) => ({
          ...m,
          proposed_memories: m.proposed_memories?.filter((pm) => pm.id !== memId),
        }))
      );
      if (showMemoryPanel) loadMemories();
    } catch (err) {
      alert("Failed to update memory preference");
    }
  }

  async function handleToggleMemorySetting() {
    if (!memorySettings) return;
    try {
      const updated = await api.updateAssistantSettings({
        memory_enabled: !memorySettings.memory_enabled,
      });
      setMemorySettings(updated);
    } catch (err) {
      alert("Failed to toggle memory system");
    }
  }

  async function handleSaveRecommendation(card: AssistantCard) {
    if (!card.id) return;
    const key = `${card.card_type}_${card.id}`;
    try {
      await api.saveAssistantRecommendation({
        entity_type: card.card_type,
        entity_id: card.id,
        title: card.title,
        reason: card.subtitle || card.description,
      });
      setSavedRecMap((prev) => ({ ...prev, [key]: true }));
    } catch (err) {
      alert("Failed to save recommendation");
    }
  }

  function copyToClipboard(text: string, msgId: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <AppShell title="AI Assistant">
      <div
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "300px 1fr",
          gap: 20,
          height: "calc(100vh - 100px)",
          padding: "12px 14px 24px",
        }}
      >
        {/* LEFT SIDEBAR: CONVERSATION MANAGER */}
        <aside
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: 16,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
          }}
        >
          {/* Top Actions */}
          <div style={{ padding: 14, borderBottom: "1px solid var(--border-color)" }}>
            <button
              onClick={startNewConversation}
              className="btn"
              style={{
                width: "100%",
                background: "var(--accent-primary)",
                color: "#fff",
                borderRadius: 10,
                padding: "9px 14px",
                fontSize: 13,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                border: "none",
                cursor: "pointer",
                marginBottom: 10,
              }}
            >
              <Plus size={16} /> New Chat
            </button>

            {/* Search Input */}
            <div style={{ position: "relative" }}>
              <Search
                size={14}
                color="var(--text-secondary)"
                style={{ position: "absolute", left: 10, top: 10 }}
              />
              <input
                type="text"
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "7px 10px 7px 32px",
                  borderRadius: 8,
                  border: "1px solid var(--border-color)",
                  background: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                  fontSize: 12,
                }}
              />
            </div>
          </div>

          {/* Filter Tabs */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid var(--border-color)",
              padding: "4px 8px",
              background: "var(--bg-secondary)",
              gap: 4,
            }}
          >
            {(["active", "pinned", "archived"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilterType(tab)}
                style={{
                  flex: 1,
                  padding: "5px 8px",
                  borderRadius: 6,
                  border: "none",
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: "capitalize",
                  background: filterType === tab ? "var(--bg-card)" : "transparent",
                  color: filterType === tab ? "var(--accent-primary)" : "var(--text-secondary)",
                  cursor: "pointer",
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Conversations List */}
          <div style={{ flex: 1, overflowY: "auto", padding: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {conversations.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-secondary)", fontSize: 12, padding: "30px 10px" }}>
                No {filterType} sessions found.
              </div>
            ) : (
              conversations.map((c) => {
                const isSelected = c.id === selectedConvId;
                const isEditing = editingConvId === c.id;

                return (
                  <div
                    key={c.id}
                    onClick={() => !isEditing && loadHistory(c.id)}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: isSelected ? "var(--bg-secondary)" : "transparent",
                      border: isSelected ? "1px solid var(--border-color)" : "1px solid transparent",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 6,
                      fontSize: 13,
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: 6 }}>
                      <MessageSquare size={14} color={isSelected ? "var(--accent-primary)" : "var(--text-secondary)"} style={{ flexShrink: 0 }} />
                      {isEditing ? (
                        <input
                          type="text"
                          value={editTitleInput}
                          onChange={(e) => setEditTitleInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveRename(c.id);
                            if (e.key === "Escape") setEditingConvId(null);
                          }}
                          onBlur={() => handleSaveRename(c.id)}
                          autoFocus
                          style={{
                            width: "100%",
                            padding: "2px 4px",
                            fontSize: 12,
                            borderRadius: 4,
                            border: "1px solid var(--accent-primary)",
                            background: "var(--bg-card)",
                            color: "var(--text-primary)",
                          }}
                        />
                      ) : (
                        <span
                          style={{
                            color: isSelected ? "var(--text-primary)" : "var(--text-secondary)",
                            fontWeight: isSelected ? 600 : 400,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {c.title}
                        </span>
                      )}
                    </div>

                    {/* Quick Row Actions */}
                    <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePin(c);
                        }}
                        title={c.pinned ? "Unpin session" : "Pin session"}
                        style={{
                          background: "none",
                          border: "none",
                          color: c.pinned ? "var(--accent-primary)" : "var(--text-secondary)",
                          cursor: "pointer",
                          padding: 2,
                          opacity: c.pinned ? 1 : 0.5,
                        }}
                      >
                        {c.pinned ? <Pin size={13} /> : <PinOff size={13} />}
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingConvId(c.id);
                          setEditTitleInput(c.title);
                        }}
                        title="Rename"
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--text-secondary)",
                          cursor: "pointer",
                          padding: 2,
                          opacity: 0.6,
                        }}
                      >
                        <Edit2 size={13} />
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleArchive(c);
                        }}
                        title={c.archived ? "Restore session" : "Archive session"}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--text-secondary)",
                          cursor: "pointer",
                          padding: 2,
                          opacity: 0.6,
                        }}
                      >
                        {c.archived ? <ArchiveRestore size={13} /> : <Archive size={13} />}
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConv(c.id);
                        }}
                        title="Delete session"
                        style={{
                          background: "none",
                          border: "none",
                          color: "#EF4444",
                          cursor: "pointer",
                          padding: 2,
                          opacity: 0.6,
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Sidebar Footer: Memory Bank Toggle */}
          <div
            style={{
              padding: 12,
              borderTop: "1px solid var(--border-color)",
              background: "var(--bg-secondary)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
              <Brain size={15} color="var(--accent-primary)" />
              <span>Memory Bank</span>
            </div>

            <button
              onClick={() => {
                setShowMemoryPanel(true);
                loadMemories();
              }}
              className="btn btn-secondary"
              style={{ padding: "4px 10px", fontSize: 11, borderRadius: 6 }}
            >
              Manage
            </button>
          </div>
        </aside>

        {/* RIGHT MAIN CHAT AREA */}
        <main
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: 16,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
          }}
        >
          {/* Top Chat Header */}
          <div
            style={{
              padding: "12px 20px",
              borderBottom: "1px solid var(--border-color)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: "var(--bg-card)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: "50%",
                  background: "rgba(83,101,245,0.1)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--accent-primary)",
                }}
              >
                <Bot size={18} />
              </div>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                  {conversations.find((c) => c.id === selectedConvId)?.title || "ALIGN Personal Intelligence Assistant"}
                </h3>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  Grounded with real ALIGN database records &amp; verified peer matching
                </span>
              </div>
            </div>

            {/* Quick settings badge */}
            {memorySettings && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 11,
                  padding: "4px 8px",
                  borderRadius: 6,
                  background: memorySettings.memory_enabled ? "rgba(16,185,129,0.1)" : "var(--bg-secondary)",
                  color: memorySettings.memory_enabled ? "#10B981" : "var(--text-secondary)",
                  fontWeight: 600,
                }}
              >
                <Brain size={13} />
                <span>{memorySettings.memory_enabled ? "Memory Active" : "Memory Paused"}</span>
              </div>
            )}
          </div>

          {/* Messages Feed */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "20px 24px",
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            {messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                      maxWidth: isUser ? "75%" : "88%",
                      flexDirection: isUser ? "row-reverse" : "row",
                    }}
                  >
                    {/* Avatar */}
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: isUser ? "var(--accent-primary)" : "rgba(83,101,245,0.1)",
                        color: isUser ? "#fff" : "var(--accent-primary)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 13,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {isUser ? <UserIcon size={16} /> : <Bot size={16} />}
                    </div>

                    {/* Content Box */}
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          padding: "12px 16px",
                          borderRadius: 14,
                          background: isUser ? "var(--accent-primary)" : "var(--bg-secondary)",
                          color: isUser ? "#fff" : "var(--text-primary)",
                          fontSize: 14,
                          lineHeight: 1.6,
                          border: isUser ? "none" : "1px solid var(--border-color)",
                        }}
                      >
                        <MarkdownView content={m.content} isUser={isUser} />
                      </div>

                      {/* Assistant Action Controls (Copy, Regenerate) */}
                      {!isUser && (
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                          <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                          <button
                            onClick={() => copyToClipboard(m.content, m.id)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--text-secondary)",
                              cursor: "pointer",
                              padding: 0,
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                            }}
                          >
                            {copiedId === m.id ? <Check size={12} color="#10B981" /> : <Copy size={12} />}
                            {copiedId === m.id ? "Copied" : "Copy"}
                          </button>

                          {m.id === messages[messages.length - 1].id && !isStreaming && (
                            <button
                              onClick={handleRegenerate}
                              style={{
                                background: "none",
                                border: "none",
                                color: "var(--text-secondary)",
                                cursor: "pointer",
                                padding: 0,
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                              }}
                            >
                              <RefreshCw size={12} /> Regenerate
                            </button>
                          )}
                        </div>
                      )}

                      {/* Proposed Memory Consent Banner */}
                      {m.proposed_memories && m.proposed_memories.length > 0 && (
                        <div
                          style={{
                            marginTop: 12,
                            padding: 12,
                            borderRadius: 10,
                            background: "rgba(83,101,245,0.06)",
                            border: "1px dashed var(--accent-primary)",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--accent-primary)", marginBottom: 8 }}>
                            <Brain size={14} /> Remember this insight for future recommendations?
                          </div>
                          {m.proposed_memories.map((pm) => (
                            <div
                              key={pm.id}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                background: "var(--bg-card)",
                                padding: "8px 12px",
                                borderRadius: 8,
                                border: "1px solid var(--border-color)",
                                marginBottom: 6,
                              }}
                            >
                              <div>
                                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-primary)", textTransform: "uppercase" }}>
                                  [{pm.type}]
                                </span>{" "}
                                <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{pm.content}</span>
                              </div>
                              <div style={{ display: "flex", gap: 6 }}>
                                <button
                                  onClick={() => handleMemoryAction(pm.id, "approved")}
                                  className="btn"
                                  style={{
                                    background: "var(--accent-primary)",
                                    color: "#fff",
                                    padding: "4px 10px",
                                    fontSize: 11,
                                    borderRadius: 6,
                                    border: "none",
                                    cursor: "pointer",
                                  }}
                                >
                                  Save Memory
                                </button>
                                <button
                                  onClick={() => handleMemoryAction(pm.id, "rejected")}
                                  className="btn btn-secondary"
                                  style={{ padding: "4px 8px", fontSize: 11, borderRadius: 6 }}
                                >
                                  Dismiss
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Rich Action Entity Cards */}
                      {m.action_cards && m.action_cards.length > 0 && (
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                            gap: 12,
                            marginTop: 14,
                          }}
                        >
                          {m.action_cards.map((card, cIdx) => {
                            const isSaved = Boolean(card.id && savedRecMap[`${card.card_type}_${card.id}`]);
                            return (
                              <div
                                key={cIdx}
                                style={{
                                  background: "var(--bg-card)",
                                  border: "1px solid var(--border-color)",
                                  borderRadius: 12,
                                  padding: 14,
                                  display: "flex",
                                  flexDirection: "column",
                                  justifyContent: "space-between",
                                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                                }}
                              >
                                <div>
                                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                                    <span
                                      style={{
                                        fontSize: 10,
                                        fontWeight: 700,
                                        textTransform: "uppercase",
                                        padding: "2px 6px",
                                        borderRadius: 4,
                                        background: "rgba(83,101,245,0.1)",
                                        color: "var(--accent-primary)",
                                      }}
                                    >
                                      {card.card_type}
                                    </span>
                                    {card.match_percentage && (
                                      <span style={{ fontSize: 11, fontWeight: 700, color: "#10B981" }}>
                                        {card.match_percentage}% Match
                                      </span>
                                    )}
                                  </div>

                                  <h4 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
                                    {card.title}
                                  </h4>

                                  {card.subtitle && (
                                    <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 6px" }}>
                                      {card.subtitle}
                                    </p>
                                  )}

                                  {card.location && (
                                    <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4, marginBottom: 8 }}>
                                      <MapPin size={12} /> {card.location}
                                    </div>
                                  )}
                                </div>

                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 8, borderTop: "1px solid var(--border-color)" }}>
                                  <Link
                                    to={card.link || "#"}
                                    style={{
                                      fontSize: 12,
                                      fontWeight: 600,
                                      color: "var(--accent-primary)",
                                      textDecoration: "none",
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: 4,
                                    }}
                                  >
                                    View <ExternalLink size={12} />
                                  </Link>

                                  <button
                                    onClick={() => handleSaveRecommendation(card)}
                                    title={isSaved ? "Saved" : "Save recommendation"}
                                    style={{
                                      background: "none",
                                      border: "none",
                                      color: isSaved ? "var(--accent-primary)" : "var(--text-secondary)",
                                      cursor: "pointer",
                                      padding: 4,
                                    }}
                                  >
                                    {isSaved ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Suggested Followup Chips */}
                      {m.suggested_prompts && m.suggested_prompts.length > 0 && !isStreaming && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
                          {m.suggested_prompts.map((p, pIdx) => (
                            <button
                              key={pIdx}
                              onClick={() => handleSend(p)}
                              style={{
                                padding: "5px 12px",
                                borderRadius: 999,
                                background: "var(--bg-secondary)",
                                border: "1px solid var(--border-color)",
                                color: "var(--text-primary)",
                                fontSize: 12,
                                fontWeight: 500,
                                cursor: "pointer",
                              }}
                            >
                              {p}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Chat Input Form */}
          <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border-color)", background: "var(--bg-card)" }}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              style={{
                display: "flex",
                gap: 10,
                alignItems: "flex-end",
              }}
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about peers, communities, goal milestones, hackathons, or third places..."
                rows={2}
                disabled={isStreaming}
                style={{
                  flex: 1,
                  padding: "10px 14px",
                  borderRadius: 12,
                  border: "1px solid var(--border-color)",
                  background: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                  fontSize: 13,
                  resize: "none",
                  fontFamily: "inherit",
                }}
              />

              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStopGeneration}
                  className="btn"
                  style={{
                    background: "#EF4444",
                    color: "#fff",
                    borderRadius: 10,
                    padding: "10px 16px",
                    fontWeight: 600,
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    border: "none",
                    cursor: "pointer",
                    height: 44,
                  }}
                >
                  <Square size={14} /> Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="btn"
                  style={{
                    background: input.trim() ? "var(--accent-primary)" : "var(--bg-secondary)",
                    color: input.trim() ? "#fff" : "var(--text-secondary)",
                    borderRadius: 10,
                    padding: "10px 18px",
                    fontWeight: 600,
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    border: "none",
                    cursor: input.trim() ? "pointer" : "default",
                    height: 44,
                  }}
                >
                  <Send size={15} /> Send
                </button>
              )}
            </form>
          </div>
        </main>

        {/* MODAL / DRAWER: MY MEMORY BANK */}
        {showMemoryPanel && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0,0,0,0.6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 100,
              padding: 16,
            }}
          >
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 16,
                padding: 24,
                width: "100%",
                maxWidth: 620,
                maxHeight: "85vh",
                overflowY: "auto",
                boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Brain size={20} color="var(--accent-primary)" />
                  <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                    My Persistent Memory Bank
                  </h3>
                </div>
                <button
                  onClick={() => setShowMemoryPanel(false)}
                  style={{ background: "none", border: "none", color: "var(--text-secondary)", cursor: "pointer" }}
                >
                  <X size={18} />
                </button>
              </div>

              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
                Memories help ALIGN personalize your recommendations. Only approved memories are retrieved, and you can edit or purge them anytime.
              </p>

              {/* Master Memory Toggle */}
              {memorySettings && (
                <div
                  style={{
                    background: "var(--bg-secondary)",
                    padding: "12px 16px",
                    borderRadius: 10,
                    border: "1px solid var(--border-color)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 20,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                      Enable Assistant Memory
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      When paused, no background extraction or memory retrieval will occur.
                    </div>
                  </div>
                  <button
                    onClick={handleToggleMemorySetting}
                    style={{
                      background: memorySettings.memory_enabled ? "var(--accent-primary)" : "var(--border-color)",
                      color: "#fff",
                      border: "none",
                      borderRadius: 20,
                      padding: "6px 14px",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    {memorySettings.memory_enabled ? "Active" : "Paused"}
                  </button>
                </div>
              )}

              {/* Memories List */}
              <div style={{ marginBottom: 20 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
                  Stored Memories ({memories.length})
                </h4>

                {loadingMemories ? (
                  <div style={{ padding: 20, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
                    Loading memories...
                  </div>
                ) : memories.length === 0 ? (
                  <div style={{ padding: 24, textAlign: "center", color: "var(--text-secondary)", fontSize: 13, background: "var(--bg-secondary)", borderRadius: 10 }}>
                    No memories stored yet. As you chat, the assistant will suggest saving skills or learning goals.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {memories.map((m) => (
                      <div
                        key={m.id}
                        style={{
                          padding: "10px 14px",
                          borderRadius: 8,
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-color)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div>
                          <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--accent-primary)" }}>
                            [{m.type}]
                          </span>{" "}
                          <span style={{ fontSize: 13, color: "var(--text-primary)" }}>{m.content}</span>
                          <span
                            style={{
                              marginLeft: 8,
                              fontSize: 10,
                              fontWeight: 600,
                              padding: "1px 6px",
                              borderRadius: 4,
                              background: m.status === "approved" ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)",
                              color: m.status === "approved" ? "#10B981" : "#F59E0B",
                            }}
                          >
                            {m.status}
                          </span>
                        </div>

                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            onClick={async () => {
                              await api.deleteAssistantMemory(m.id);
                              loadMemories();
                            }}
                            style={{ background: "none", border: "none", color: "#EF4444", cursor: "pointer", padding: 4 }}
                            title="Delete memory"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Clear All Button */}
              {memories.length > 0 && (
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    onClick={async () => {
                      if (confirm("Are you sure you want to permanently clear all memories?")) {
                        await api.clearAllAssistantMemories();
                        loadMemories();
                      }
                    }}
                    className="btn btn-secondary"
                    style={{ padding: "6px 14px", fontSize: 12, color: "#EF4444" }}
                  >
                    Clear All Memories
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
