# Future widget extensions

## Typing indicator

- UI slot: `.bfw-typing-slot` in `WidgetApp.tsx` (`data-active` toggles reserved height).
- Wire to: optimistic “assistant is typing” after send, or SSE/WebSocket events later.

## Reconnect / resilience

- Persist `visitor_session_key` + `conversation_id` (already in `sessionStorage`).
- Add backoff wrapper around `fetch` in `publicWidgetApi.ts` with `ConnectionHealth` from `types.ts`.
- Optional: `visibilitychange` refetch bootstrap when tab wakes.

## Streaming

- Introduce `ChatTransportKind = "http-json" | "sse"` in `types.ts`.
- Split `postPublicChat` into `startChatTurn` + stream reader; append assistant tokens to the last message row.
- Keep HTTP JSON path as fallback when streaming unavailable.
