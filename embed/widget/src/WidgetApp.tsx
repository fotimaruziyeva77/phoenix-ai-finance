import { useCallback, useEffect, useMemo, useRef, useState } from "preact/hooks";
import { fetchWidgetBootstrap, postPublicChat } from "./api/publicWidgetApi";
import type { ChatMessageRow, WidgetBootstrap, WidgetInitOptions, WidgetLang } from "./types";

const WIDGET_I18N: Record<WidgetLang, Record<string, string>> = {
  en: {
    openChat: "Open chat",
    closeChat: "Close chat",
    closePanel: "Close chat panel",
    connecting: "Connecting…",
    emptyPrompt: "Send a message to start the conversation.",
    placeholder: "Type a message…",
    send: "Send",
    sending: "Sending…",
    you: "You",
    assistant: "Assistant",
    poweredBy: "Powered by",
  },
  uz: {
    openChat: "Chatni ochish",
    closeChat: "Chatni yopish",
    closePanel: "Chat panelini yopish",
    connecting: "Ulanmoqda…",
    emptyPrompt: "Suhbatni boshlash uchun xabar yozing.",
    placeholder: "Xabar yozing…",
    send: "Yuborish",
    sending: "Yuborilmoqda…",
    you: "Siz",
    assistant: "Yordamchi",
    poweredBy: "Ishlab chiqaruvchi:",
  },
  ru: {
    openChat: "Открыть чат",
    closeChat: "Закрыть чат",
    closePanel: "Закрыть панель чата",
    connecting: "Подключение…",
    emptyPrompt: "Отправьте сообщение, чтобы начать беседу.",
    placeholder: "Введите сообщение…",
    send: "Отправить",
    sending: "Отправка…",
    you: "Вы",
    assistant: "Ассистент",
    poweredBy: "Работает на",
  },
};

const SESSION_PREFIX = "bfw_sess_v1:";

function storageKey(publicKey: string): string {
  return `${SESSION_PREFIX}${publicKey}`;
}

function loadPersistedSession(
  publicKey: string,
): { visitorSessionKey: string | null; conversationId: string | null } {
  try {
    const raw = sessionStorage.getItem(storageKey(publicKey));
    if (!raw) return { visitorSessionKey: null, conversationId: null };
    const o = JSON.parse(raw) as { visitor_session_key?: string; conversation_id?: string };
    return {
      visitorSessionKey: typeof o.visitor_session_key === "string" ? o.visitor_session_key : null,
      conversationId: typeof o.conversation_id === "string" ? o.conversation_id : null,
    };
  } catch {
    return { visitorSessionKey: null, conversationId: null };
  }
}

function savePersistedSession(
  publicKey: string,
  visitorSessionKey: string,
  conversationId: string,
): void {
  try {
    sessionStorage.setItem(
      storageKey(publicKey),
      JSON.stringify({
        visitor_session_key: visitorSessionKey,
        conversation_id: conversationId,
      }),
    );
  } catch {
    /* quota / private mode */
  }
}

function resolveThemeToken(theme: string | null | undefined): "light" | "dark" {
  const t = (theme || "").toLowerCase();
  if (t.includes("dark")) return "dark";
  return "light";
}

function IconChat() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3C7.03 3 3 6.58 3 11c0 1.79.68 3.45 1.84 4.79L3.5 20.5l4.85-1.28A8.94 8.94 0 0012 19c4.97 0 9-3.58 9-8s-4.03-8-9-8z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <circle cx="8.5" cy="11" r="1.15" fill="currentColor" />
      <circle cx="12" cy="11" r="1.15" fill="currentColor" />
      <circle cx="15.5" cy="11" r="1.15" fill="currentColor" />
    </svg>
  );
}

function IconClose() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

type Props = WidgetInitOptions;

export function WidgetApp(props: Props) {
  const { publicKey, apiBaseUrl, position = "bottom-right" } = props;

  const [open, setOpen] = useState(false);
  const [bootstrap, setBootstrap] = useState<WidgetBootstrap | null>(null);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageRow[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const persisted = useMemo(() => loadPersistedSession(publicKey), [publicKey]);
  const [visitorSessionKey, setVisitorSessionKey] = useState<string | null>(persisted.visitorSessionKey);
  const [conversationId, setConversationId] = useState<string | null>(persisted.conversationId);

  const chatAbortRef = useRef<AbortController | null>(null);
  const listEndRef = useRef<HTMLDivElement | null>(null);

  const theme = resolveThemeToken(bootstrap?.theme ?? null);
  const sideClass = position === "bottom-left" ? "bfw-launcher--left" : "bfw-launcher--right";
  const panelSide = position === "bottom-left" ? "bfw-panel--left" : "bfw-panel--right";

  const scrollToBottom = useCallback(() => {
    queueMicrotask(() => listEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }));
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending, scrollToBottom]);

  useEffect(() => {
    if (!open) return;
    if (bootstrap !== null) return;

    let cancelled = false;
    const ac = new AbortController();
    setBootstrapLoading(true);
    setBootstrapError(null);

    fetchWidgetBootstrap(apiBaseUrl, publicKey, ac.signal)
      .then((b) => {
        if (!cancelled) setBootstrap(b);
      })
      .catch((e: Error) => {
        if (cancelled || e.name === "AbortError") return;
        setBootstrapError(e.message || "Could not load chat.");
      })
      .finally(() => {
        if (!cancelled) setBootstrapLoading(false);
      });

    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [open, apiBaseUrl, publicKey, bootstrap]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending || bootstrapError) return;

    setSending(true);
    setSendError(null);
    chatAbortRef.current?.abort();
    const ac = new AbortController();
    chatAbortRef.current = ac;

    try {
      const res = await postPublicChat(
        apiBaseUrl,
        publicKey,
        {
          message: text,
          visitor_session_key: visitorSessionKey,
          conversation_id: conversationId,
        },
        ac.signal,
      );

      setVisitorSessionKey(res.visitor_session_key);
      setConversationId(res.conversation_id);
      savePersistedSession(publicKey, res.visitor_session_key, res.conversation_id);

      setMessages((prev) => [
        ...prev,
        { id: res.user_message_id, role: "user", text },
        { id: res.assistant_message_id, role: "assistant", text: res.assistant_text },
      ]);
      setInput("");
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      const msg = e instanceof Error ? e.message : "Message could not be sent.";
      setSendError(msg);
    } finally {
      setSending(false);
      chatAbortRef.current = null;
    }
  }, [
    input,
    sending,
    bootstrapError,
    apiBaseUrl,
    publicKey,
    visitorSessionKey,
    conversationId,
  ]);

  const onKeyDown = (ev: KeyboardEvent) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      void handleSend();
    }
  };

  const title = bootstrap?.bot_display_name ?? "Chat";

  return (
    <div class="bfw-root" data-bfw-theme={theme}>
      <button
        type="button"
        class={`bfw-launcher ${sideClass}`}
        data-open={open ? "true" : "false"}
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close chat" : "Open chat"}
        aria-expanded={open}
      >
        {open ? <IconClose /> : <IconChat />}
      </button>

      {open ? (
        <section
          class={`bfw-panel ${panelSide}`}
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          <header class="bfw-header">
            <div>
              <h2 class="bfw-header-title">{title}</h2>
            </div>
            <button
              type="button"
              class="bfw-icon-btn"
              onClick={() => setOpen(false)}
              aria-label="Close chat panel"
            >
              <IconClose />
            </button>
          </header>

          {bootstrapLoading ? (
            <div class="bfw-loading" role="status">
              <span class="bfw-spinner" aria-hidden="true" />
              <span>Connecting…</span>
            </div>
          ) : bootstrapError ? (
            <div class="bfw-messages">
              <p class="bfw-error" role="alert">
                {bootstrapError}
              </p>
            </div>
          ) : (
            <>
              {bootstrap?.welcome_text ? (
                <div class="bfw-welcome">{bootstrap.welcome_text}</div>
              ) : null}

              <div class="bfw-messages" role="log" aria-live="polite" aria-relevant="additions">
                {messages.length === 0 ? (
                  <p class="bfw-header-sub" style={{ margin: "8px 0", textAlign: "center" }}>
                    Send a message to start the conversation.
                  </p>
                ) : null}
                {messages.map((m) => (
                  <article
                    key={m.id}
                    class={`bfw-msg bfw-msg--${m.role}`}
                    aria-label={m.role === "user" ? "You" : "Assistant"}
                  >
                    <p class="bfw-msg-text">{m.text}</p>
                  </article>
                ))}
                {sending ? (
                  <div class="bfw-loading" style={{ padding: "12px 0" }} role="status">
                    <span class="bfw-spinner" aria-hidden="true" />
                    <span>Sending…</span>
                  </div>
                ) : null}
                <div ref={listEndRef} />
              </div>

              {/* Hook for future typing indicator UI */}
              <div class="bfw-typing-slot" data-active="false" aria-hidden="true" />

              <footer class="bfw-footer">
                {sendError ? (
                  <p class="bfw-error" role="alert">
                    {sendError}
                  </p>
                ) : null}
                <div class="bfw-form">
                  <textarea
                    class="bfw-input"
                    rows={1}
                    placeholder="Type a message…"
                    value={input}
                    onInput={(e) => setInput((e.target as HTMLTextAreaElement).value)}
                    onKeyDown={onKeyDown}
                    disabled={sending}
                    aria-label="Message"
                  />
                  <button
                    type="button"
                    class="bfw-send"
                    onClick={() => void handleSend()}
                    disabled={sending || !input.trim()}
                  >
                    Send
                  </button>
                </div>
                {bootstrap?.show_branding !== false && (
                  <div class="bfw-branding">
                    <a
                      href="https://botforge.ai"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="bfw-branding-link"
                    >
                      Powered by <strong>BotForge</strong>
                    </a>
                  </div>
                )}
              </footer>
            </>
          )}
        </section>
      ) : null}
    </div>
  );
}
