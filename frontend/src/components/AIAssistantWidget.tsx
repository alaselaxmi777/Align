import { FormEvent, useEffect, useRef, useState } from "react";
import {
  Bot,
  Brain,
  Calendar,
  CheckCircle,
  ChevronDown,
  Compass,
  CornerDownLeft,
  ExternalLink,
  Layers,
  MapPin,
  Maximize2,
  MessageSquare,
  Minimize2,
  Send,
  Sparkles,
  User as UserIcon,
  X,
  Square,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api, AssistantCard, AssistantProposedMemory } from "../lib/api";
import MarkdownView from "./common/MarkdownView";

const PRESET_PROMPTS = [
  "Find people interested in AI near me",
  "Recommend communities for learning programming",
  "Find upcoming technology events",
  "Help me achieve my career goals",
];

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  action_cards?: AssistantCard[];
  suggested_prompts?: string[];
  proposed_memories?: AssistantProposedMemory[];
  created_at: string;
}

export default function AIAssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<number | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I am your ALIGN Discovery Assistant. Ask me to find like-minded peers, recommend active learning communities, track tech events, or build an AI Goal Journey.",
      suggested_prompts: PRESET_PROMPTS,
      created_at: new Date().toISOString(),
    },
  ]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, isStreaming]);

  async function handleSend(textToSend?: string) {
    const query = (textToSend || input).trim();
    if (!query || isStreaming) return;

    if (!loggedIn) {
      navigate("/login");
      return;
    }

    setInput("");
    const userMsgId = String(Date.now());
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: query,
      created_at: new Date().toISOString(),
    };

    const assistantMsgId = String(Date.now() + 1);
    const initialAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      action_cards: [],
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
        query,
        conversationId,
        (eventName, data) => {
          if (eventName === "session") {
            if (data.conversation_id) setConversationId(data.conversation_id);
          } else if (eventName === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, content: m.content + (data.token || "") } : m
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
                  ? { ...m, proposed_memories: [...(m.proposed_memories || []), data] }
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
                    "I encountered an error connecting to ALIGN discovery services. Please verify your connection.",
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }

  function handleStop() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }

  async function handleMemoryConsent(memId: number, status: "approved" | "rejected") {
    try {
      await api.updateAssistantMemory(memId, { status });
      setMessages((prev) =>
        prev.map((m) => ({
          ...m,
          proposed_memories: m.proposed_memories?.filter((pm) => pm.id !== memId),
        }))
      );
    } catch (err) {
      alert("Failed to update memory");
    }
  }

  function renderCard(card: AssistantCard, idx: number) {
    return (
      <div
        key={idx}
        onClick={() => {
          navigate(card.link);
          setIsOpen(false);
        }}
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-color)",
          borderRadius: "10px",
          padding: "9px 12px",
          marginTop: "6px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: "rgba(83, 101, 245, 0.12)",
            color: "var(--accent-primary)",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          {card.card_type === "user" && <UserIcon size={16} />}
          {card.card_type === "community" && <Layers size={16} />}
          {card.card_type === "event" && <Calendar size={16} />}
          {card.card_type === "place" && <MapPin size={16} />}
          {card.card_type === "opportunity" && <Sparkles size={16} />}
          {card.card_type === "action_cta" && <Sparkles size={16} />}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--text-primary)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {card.title}
            </span>
            {card.match_percentage && (
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#10B981" }}>
                {card.match_percentage}%
              </span>
            )}
          </div>
          {card.subtitle && (
            <p
              style={{
                fontSize: "11px",
                color: "var(--text-secondary)",
                margin: "2px 0 0 0",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {card.subtitle}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Floating Trigger Bubble */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-[80px] md:bottom-6 right-4 md:right-6 z-40 px-4 py-2.5 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-xs shadow-xl hover:brightness-105 transition-all flex items-center gap-2 border border-[var(--lime)]"
        >
          <Sparkles size={16} />
          <span>Ask ALIGN</span>
        </button>
      )}

      {/* Floating Assistant Drawer */}
      {isOpen && (
        <div
          className="fixed bottom-[80px] md:bottom-6 right-4 md:right-6 z-50 w-[390px] max-w-[calc(100vw-32px)] h-[580px] max-h-[calc(100vh-100px)] bg-[var(--bg-elev)] border border-[var(--border)] rounded-[28px] shadow-2xl flex flex-col overflow-hidden backdrop-blur-xl"
        >
          {/* Header */}
          <div
            style={{
              padding: "14px 18px",
              background: "rgba(167, 121, 232, 0.08)",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "8px",
                  background: "var(--lilac)",
                  color: "#1C1126",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <Bot size={15} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  ALIGN Assistant
                </h4>
                <span style={{ fontSize: "10px", color: "var(--text-secondary)" }}>
                  Grounded with real platform records
                </span>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <button
                onClick={() => {
                  setIsOpen(false);
                  navigate("/assistant");
                }}
                title="Expand to Full Page"
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  padding: "4px",
                }}
              >
                <Maximize2 size={15} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  padding: "4px",
                }}
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Chat Messages Log */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: m.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "88%",
                    padding: "10px 12px",
                    borderRadius: "12px",
                    fontSize: "13px",
                    lineHeight: "1.45",
                    background: m.role === "user" ? "var(--accent-primary)" : "var(--bg-secondary)",
                    color: m.role === "user" ? "#FFFFFF" : "var(--text-primary)",
                    border: m.role === "user" ? "none" : "1px solid var(--border-color)",
                  }}
                >
                  <MarkdownView content={m.content} isUser={m.role === "user"} />
                </div>

                {/* Proposed Memory Consent Prompt */}
                {m.proposed_memories && m.proposed_memories.length > 0 && (
                  <div
                    style={{
                      width: "88%",
                      marginTop: "6px",
                      padding: "8px 10px",
                      borderRadius: "8px",
                      background: "rgba(83,101,245,0.06)",
                      border: "1px dashed var(--accent-primary)",
                      fontSize: "11px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 700, color: "var(--accent-primary)", marginBottom: 4 }}>
                      <Brain size={12} /> Remember this?
                    </div>
                    {m.proposed_memories.map((pm) => (
                      <div key={pm.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ color: "var(--text-primary)" }}>{pm.content}</span>
                        <div style={{ display: "flex", gap: 4 }}>
                          <button
                            onClick={() => handleMemoryConsent(pm.id, "approved")}
                            style={{
                              background: "var(--accent-primary)",
                              color: "#fff",
                              border: "none",
                              borderRadius: 4,
                              padding: "2px 6px",
                              fontSize: 10,
                              cursor: "pointer",
                            }}
                          >
                            Save
                          </button>
                          <button
                            onClick={() => handleMemoryConsent(pm.id, "rejected")}
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--text-secondary)",
                              padding: "2px 4px",
                              fontSize: 10,
                              cursor: "pointer",
                            }}
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action Cards */}
                {m.action_cards && m.action_cards.length > 0 && (
                  <div style={{ width: "95%", marginTop: "6px" }}>
                    {m.action_cards.slice(0, 3).map((card, idx) => renderCard(card, idx))}
                  </div>
                )}

                {/* Prompt Suggestions */}
                {m.suggested_prompts && m.suggested_prompts.length > 0 && !isStreaming && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "5px", marginTop: "8px" }}>
                    {m.suggested_prompts.slice(0, 3).map((p, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(p)}
                        style={{
                          fontSize: "11px",
                          fontWeight: 500,
                          padding: "4px 10px",
                          borderRadius: "999px",
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-color)",
                          color: "var(--text-primary)",
                          cursor: "pointer",
                        }}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              void handleSend();
            }}
            style={{
              padding: "10px 12px",
              borderTop: "1px solid var(--border-color)",
              background: "var(--bg-card)",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about ALIGN..."
              disabled={isStreaming}
              style={{
                flex: 1,
                height: "36px",
                fontSize: "13px",
                padding: "0 12px",
                borderRadius: "999px",
                border: "1px solid var(--border-color)",
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
              }}
            />
            {isStreaming ? (
              <button
                type="button"
                onClick={handleStop}
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "50%",
                  background: "#EF4444",
                  color: "#FFFFFF",
                  border: "none",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                }}
              >
                <Square size={14} />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "50%",
                  background: input.trim() ? "var(--accent-primary)" : "var(--bg-secondary)",
                  color: input.trim() ? "#FFFFFF" : "var(--text-secondary)",
                  border: "none",
                  display: "grid",
                  placeItems: "center",
                  cursor: input.trim() ? "pointer" : "default",
                }}
              >
                <Send size={15} />
              </button>
            )}
          </form>
        </div>
      )}
    </>
  );
}
