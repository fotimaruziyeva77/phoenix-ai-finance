"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useNotifications } from "@/hooks/useNotifications";
import type { NotificationItem } from "@/lib/api/notifications";

import styles from "./notification-bell.module.css";

function timeAgo(iso: string, lang: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) {
    return lang === "uz" ? "hozirgina" : lang === "ru" ? "только что" : "just now";
  }
  if (mins < 60) {
    return lang === "uz" ? `${mins} daqiqa oldin` : lang === "ru" ? `${mins} мин. назад` : `${mins}m ago`;
  }
  const hours = Math.floor(mins / 60);
  if (hours < 24) {
    return lang === "uz" ? `${hours} soat oldin` : lang === "ru" ? `${hours} ч. назад` : `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return lang === "uz" ? `${days} kun oldin` : lang === "ru" ? `${days} дн. назад` : `${days}d ago`;
}

export function NotificationBell() {
  const { t, lang } = useLanguage();
  const { items, unreadCount, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  const toggle = useCallback(() => setOpen((o) => !o), []);

  const handleItemClick = useCallback(
    (item: NotificationItem) => {
      if (!item.isRead) {
        void markRead(item.id);
      }
    },
    [markRead],
  );

  const handleMarkAllRead = useCallback(() => {
    void markAllRead();
  }, [markAllRead]);

  const badgeLabel = unreadCount > 99 ? "99+" : String(unreadCount);

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.bellBtn}
        aria-label={String(t("dashboard.notifications.bell"))}
        aria-expanded={open}
        onClick={toggle}
      >
        <svg className={styles.bellIcon} viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M18 8A6 6 0 1 0 6 8c0 7-3 9-3 9h18s-3-2-3-9ZM13.73 21a2 2 0 0 1-3.46 0"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {unreadCount > 0 && (
          <span className={styles.badge} aria-label={`${unreadCount} unread`}>
            {badgeLabel}
          </span>
        )}
      </button>

      {open && (
        <div className={styles.dropdown} role="dialog" aria-label="Notifications">
          <div className={styles.dropdownHeader}>
            <p className={styles.dropdownTitle}>
              {String(t("dashboard.notifications.title"))}
            </p>
            {unreadCount > 0 && (
              <button
                type="button"
                className={styles.markAllBtn}
                onClick={handleMarkAllRead}
              >
                {String(t("dashboard.notifications.markAllRead"))}
              </button>
            )}
          </div>

          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <svg className={styles.emptyIcon} viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                  d="M18 8A6 6 0 1 0 6 8c0 7-3 9-3 9h18s-3-2-3-9ZM13.73 21a2 2 0 0 1-3.46 0"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <p className={styles.emptyText}>
                {String(t("dashboard.notifications.empty"))}
              </p>
            </div>
          ) : (
            <div className={styles.notifList}>
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`${styles.notifItem} ${!item.isRead ? styles.notifUnread : ""}`}
                  onClick={() => handleItemClick(item)}
                >
                  <span
                    className={`${styles.notifDot} ${item.isRead ? styles.notifDotRead : ""}`}
                  />
                  <div className={styles.notifContent}>
                    <p className={styles.notifTitle}>{item.title}</p>
                    {item.body && <p className={styles.notifBody}>{item.body}</p>}
                    <p className={styles.notifTime}>{timeAgo(item.createdAt, lang)}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
