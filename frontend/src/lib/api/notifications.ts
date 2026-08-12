import { apiFetchWithAuth } from "@/lib/api/client";

// ─── Types ───────────────────────────────────────────────────────────────────

export type NotificationItemDto = {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  reference_id: string | null;
  reference_type: string | null;
  is_read: boolean;
  created_at: string;
};

export type NotificationListResponseDto = {
  items: NotificationItemDto[];
  unread_count: number;
};

export type UnreadCountResponseDto = {
  unread_count: number;
};

export type MarkReadResponseDto = {
  success: boolean;
};

export type MarkAllReadResponseDto = {
  marked_count: number;
};

// ─── Mapped types ────────────────────────────────────────────────────────────

export type NotificationItem = {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  referenceId: string | null;
  referenceType: string | null;
  isRead: boolean;
  createdAt: string;
};

function mapItem(dto: NotificationItemDto): NotificationItem {
  return {
    id: dto.id,
    kind: dto.kind,
    title: dto.title,
    body: dto.body,
    referenceId: dto.reference_id,
    referenceType: dto.reference_type,
    isRead: dto.is_read,
    createdAt: dto.created_at,
  };
}

// ─── API functions ───────────────────────────────────────────────────────────

export async function fetchNotifications(
  accessToken: string | null,
  opts: { limit?: number; offset?: number; unreadOnly?: boolean } = {},
): Promise<{ items: NotificationItem[]; unreadCount: number }> {
  const p = new URLSearchParams();
  if (opts.limit) p.set("limit", String(opts.limit));
  if (opts.offset) p.set("offset", String(opts.offset));
  if (opts.unreadOnly) p.set("unread_only", "true");
  const qs = p.toString();
  const path = `/api/v1/notifications${qs ? `?${qs}` : ""}`;
  const data = await apiFetchWithAuth<NotificationListResponseDto>(path, accessToken);
  return {
    items: data.items.map(mapItem),
    unreadCount: data.unread_count,
  };
}

export async function fetchUnreadCount(
  accessToken: string | null,
): Promise<number> {
  const data = await apiFetchWithAuth<UnreadCountResponseDto>(
    "/api/v1/notifications/unread-count",
    accessToken,
  );
  return data.unread_count;
}

export async function markNotificationRead(
  accessToken: string | null,
  notificationId: string,
): Promise<boolean> {
  const data = await apiFetchWithAuth<MarkReadResponseDto>(
    `/api/v1/notifications/${notificationId}/read`,
    accessToken,
    { method: "PATCH" },
  );
  return data.success;
}

export async function markAllNotificationsRead(
  accessToken: string | null,
): Promise<number> {
  const data = await apiFetchWithAuth<MarkAllReadResponseDto>(
    "/api/v1/notifications/read-all",
    accessToken,
    { method: "PATCH" },
  );
  return data.marked_count;
}
