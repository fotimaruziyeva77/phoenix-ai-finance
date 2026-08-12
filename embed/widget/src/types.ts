/**
 * Public API contracts (mirrors backend schemas). Kept local — no imports from dashboard app.
 */

export type WidgetBootstrap = {
  is_enabled: boolean;
  welcome_text: string | null;
  theme: string | null;
  bot_display_name: string;
  show_branding?: boolean;
};

export type PublicChatRequest = {
  message: string;
  visitor_session_key?: string | null;
  conversation_id?: string | null;
};

export type PublicChatResponse = {
  conversation_id: string;
  visitor_session_key: string;
  user_message_id: string;
  assistant_message_id: string;
  assistant_text: string;
  bot_display_name: string;
};

export type StandardApiError = {
  error: {
    code: string;
    message: string;
    request_id?: string | null;
    category?: string | null;
  };
};

/** Current transport; SSE/WebSocket can be added without breaking this surface. */
export type ChatTransportKind = "http-json";

/** Placeholder for future reconnect / backoff state machines. */
export type ConnectionHealth = "idle" | "online" | "degraded";

export type ChatMessageRow = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

export type WidgetLang = "en" | "uz" | "ru";

export type WidgetInitOptions = {
  publicKey: string;
  /** API origin only, e.g. https://api.example.com (no trailing slash). */
  apiBaseUrl: string;
  position?: "bottom-right" | "bottom-left";
  zIndex?: number;
  language?: WidgetLang;
};
