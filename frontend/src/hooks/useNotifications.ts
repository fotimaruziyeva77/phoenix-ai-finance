"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  fetchNotifications,
  fetchUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  type NotificationItem,
} from "@/lib/api/notifications";

export type UseNotificationsResult = {
  /** Recent notification items. */
  items: NotificationItem[];
  /** Total unread count (for badge). */
  unreadCount: number;
  /** Whether the initial fetch is in progress. */
  loading: boolean;
  /** Refetch items + count. */
  refetch: () => void;
  /** Mark a single notification as read (optimistic). */
  markRead: (id: string) => Promise<void>;
  /** Mark all as read (optimistic). */
  markAllRead: () => Promise<void>;
};

const POLL_INTERVAL_MS = 30_000; // 30 s

export function useNotifications(): UseNotificationsResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setItems([]);
      setUnreadCount(0);
      setLoading(false);
      return;
    }
    try {
      const { items: fetched, unreadCount: uc } = await fetchNotifications(accessToken, {
        limit: 30,
      });
      setItems(fetched);
      setUnreadCount(uc);
    } catch {
      // silently ignore — bell stays at 0
    } finally {
      setLoading(false);
    }
  }, [accessToken, canUseAuthenticatedApi]);

  // Poll unread count only (lightweight)
  const pollCount = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    try {
      const uc = await fetchUnreadCount(accessToken);
      setUnreadCount(uc);
    } catch {
      /* ignore */
    }
  }, [accessToken, canUseAuthenticatedApi]);

  // Initial load
  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  // Polling
  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    intervalRef.current = setInterval(() => void pollCount(), POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [hydrated, canUseAuthenticatedApi, pollCount]);

  const markRead = useCallback(
    async (id: string) => {
      // Optimistic update — only decrement the badge if this item was actually unread,
      // otherwise re-clicking an already-read item drifts the count below the true total.
      let wasUnread = false;
      setItems((prev) =>
        prev.map((n) => {
          if (n.id === id && !n.isRead) {
            wasUnread = true;
            return { ...n, isRead: true };
          }
          return n;
        }),
      );
      if (wasUnread) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
      try {
        await markNotificationRead(accessToken, id);
      } catch {
        // revert on failure
        void load();
      }
    },
    [accessToken, load],
  );

  const markAllRead = useCallback(async () => {
    // Optimistic
    setItems((prev) => prev.map((n) => ({ ...n, isRead: true })));
    setUnreadCount(0);
    try {
      await markAllNotificationsRead(accessToken);
    } catch {
      void load();
    }
  }, [accessToken, load]);

  return { items, unreadCount, loading, refetch: load, markRead, markAllRead };
}
