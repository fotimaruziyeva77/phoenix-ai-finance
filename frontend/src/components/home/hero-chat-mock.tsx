"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import styles from "./hero.module.css";

/* ─── Conversation scripts in 5 languages ─── */

type Msg = { from: "user" | "bot"; text: string };
type Script = { lang: string; flag: string; messages: Msg[] };

const SCRIPTS: Script[] = [
  {
    lang: "English",
    flag: "🇺🇸",
    messages: [
      { from: "user", text: "Hi! I need a chatbot for my online store." },
      { from: "bot", text: "Great choice! What products do you sell? I'll tailor the bot for your niche." },
      { from: "user", text: "We sell organic skincare products." },
      { from: "bot", text: "Perfect. Can I get your email so I can send you a personalized demo?" },
      { from: "user", text: "Sure — hello@skincare.com" },
      { from: "bot", text: "✅ Lead captured! Our team will reach out within 24 hours." },
    ],
  },
  {
    lang: "O'zbekcha",
    flag: "🇺🇿",
    messages: [
      { from: "user", text: "Salom! Klinikam uchun bot kerak." },
      { from: "bot", text: "Ajoyib! Qanday xizmatlar ko'rsatasiz? Bot shunga moslashtiriladi." },
      { from: "user", text: "Tish davolash va implantatsiya." },
      { from: "bot", text: "Tushunarli. Telefon raqamingizni qoldirsangiz, mutaxassis bog'lanadi." },
      { from: "user", text: "+998 90 123 45 67" },
      { from: "bot", text: "✅ Lid saqlandi! Tez orada aloqaga chiqamiz." },
    ],
  },
  {
    lang: "Русский",
    flag: "🇷🇺",
    messages: [
      { from: "user", text: "Здравствуйте! Мне нужен бот для агентства." },
      { from: "bot", text: "Отлично! Какие услуги вы предлагаете? Настроим бота под вашу нишу." },
      { from: "user", text: "Маркетинг и SMM для бизнеса." },
      { from: "bot", text: "Понял. Оставьте email — отправлю персональное предложение." },
      { from: "user", text: "info@agency.ru" },
      { from: "bot", text: "✅ Лид сохранён! Свяжемся в ближайшее время." },
    ],
  },
  {
    lang: "Türkçe",
    flag: "🇹🇷",
    messages: [
      { from: "user", text: "Merhaba! Emlak ofisim için bot istiyorum." },
      { from: "bot", text: "Harika! Hangi bölgelerde çalışıyorsunuz? Botu ona göre ayarlayalım." },
      { from: "user", text: "İstanbul, Antalya ve Bodrum." },
      { from: "bot", text: "Anladım. Telefon numaranızı bırakır mısınız?" },
      { from: "user", text: "+90 532 000 00 00" },
      { from: "bot", text: "✅ Lead kaydedildi! Ekibimiz sizinle iletişime geçecek." },
    ],
  },
  {
    lang: "العربية",
    flag: "🇸🇦",
    messages: [
      { from: "user", text: "مرحباً! أحتاج بوت لمتجري الإلكتروني." },
      { from: "bot", text: "ممتاز! ماذا تبيعون؟ سأخصص البوت لمجالكم." },
      { from: "user", text: "نبيع ملابس رجالية فاخرة." },
      { from: "bot", text: "رائع. هل يمكنك ترك بريدك الإلكتروني؟" },
      { from: "user", text: "info@luxury-store.sa" },
      { from: "bot", text: "✅ تم حفظ العميل المحتمل! سنتواصل معك قريباً." },
    ],
  },
];

const TYPING_SPEED = 35; // ms per character
const PAUSE_AFTER_MSG = 600; // ms pause between messages
const PAUSE_AFTER_SCRIPT = 2500; // ms pause before switching language
const BOT_THINK_TIME = 800; // ms "thinking" before bot types

/** Decorative animated chat preview. */
export function HeroChatMock() {
  const [scriptIdx, setScriptIdx] = useState(0);
  const [visibleMessages, setVisibleMessages] = useState<Msg[]>([]);
  const [typingText, setTypingText] = useState("");
  const [isTyping, setIsTyping] = useState<"user" | "bot" | null>(null);
  const [leadCaptured, setLeadCaptured] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef(false);

  const scrollToBottom = useCallback(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    abortRef.current = false;
    let cancelled = false;

    async function sleep(ms: number) {
      return new Promise<void>((r) => {
        const id = setTimeout(r, ms);
        // Allow cleanup
        if (cancelled) clearTimeout(id);
      });
    }

    async function typeMessage(msg: Msg) {
      if (cancelled) return;
      setIsTyping(msg.from);
      setTypingText("");

      // Bot "thinks" briefly before typing
      if (msg.from === "bot") {
        await sleep(BOT_THINK_TIME);
      }

      // Type character by character
      for (let i = 0; i <= msg.text.length; i++) {
        if (cancelled) return;
        setTypingText(msg.text.slice(0, i));
        scrollToBottom();
        await sleep(TYPING_SPEED);
      }

      if (cancelled) return;
      setIsTyping(null);
      setTypingText("");
      setVisibleMessages((prev) => [...prev, msg]);

      // Check if this is the lead captured message
      if (msg.text.startsWith("✅")) {
        setLeadCaptured(true);
      }

      scrollToBottom();
      await sleep(PAUSE_AFTER_MSG);
    }

    async function runScript(idx: number) {
      if (cancelled) return;
      const script = SCRIPTS[idx];
      if (!script) return;
      setVisibleMessages([]);
      setLeadCaptured(false);
      setTypingText("");
      setIsTyping(null);

      await sleep(600); // brief pause at start

      for (const msg of script.messages) {
        if (cancelled) return;
        await typeMessage(msg);
      }

      if (cancelled) return;
      await sleep(PAUSE_AFTER_SCRIPT);

      if (cancelled) return;
      // Move to next script
      setScriptIdx((prev) => (prev + 1) % SCRIPTS.length);
    }

    void runScript(scriptIdx);

    return () => {
      cancelled = true;
    };
  }, [scriptIdx, scrollToBottom]);

  const currentScript = SCRIPTS[scriptIdx] ?? SCRIPTS[0]!;

  return (
    <div className={styles.mockWrap} aria-hidden>
      <div className={styles.mockGlow} />
      <div className={styles.mock}>
        {/* ── Top bar ── */}
        <div className={styles.mockTop}>
          <div className={styles.mockDots}>
            <span className={styles.mockDot} />
            <span className={styles.mockDot} />
            <span className={styles.mockDot} />
          </div>
          <span className={styles.mockTitle}>
            <span className={styles.mockLangFlag}>{currentScript.flag}</span>
            {" "}
            {currentScript.lang}
          </span>
          {/* Language indicators */}
          <div className={styles.mockLangDots}>
            {SCRIPTS.map((s, i) => (
              <span
                key={s.lang}
                className={`${styles.mockLangDot} ${i === scriptIdx ? styles.mockLangDotActive : ""}`}
                title={s.lang}
              />
            ))}
          </div>
        </div>

        {/* ── Chat body ── */}
        <div className={styles.mockBody} ref={bodyRef}>
          {visibleMessages.map((msg, i) => (
            <div
              key={`${scriptIdx}-${i}`}
              className={`${styles.bubbleRow} ${msg.from === "bot" ? styles.bubbleRowBot : ""}`}
            >
              <div>
                <div
                  className={`${styles.bubble} ${msg.from === "user" ? styles.bubbleUser : styles.bubbleBot} ${styles.bubbleAnimateIn} ${msg.text.startsWith("✅") ? styles.bubbleSuccess : ""}`}
                >
                  {msg.text}
                </div>
                {msg.from === "bot" && !msg.text.startsWith("✅") && (
                  <div className={styles.bubbleMeta}>BotForge · instant reply</div>
                )}
                {msg.text.startsWith("✅") && (
                  <div className={styles.bubbleMetaSuccess}>Lead captured</div>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator / live text */}
          {isTyping && (
            <div className={`${styles.bubbleRow} ${isTyping === "bot" ? styles.bubbleRowBot : ""}`}>
              <div
                className={`${styles.bubble} ${isTyping === "user" ? styles.bubbleUser : styles.bubbleBot} ${styles.bubbleTyping}`}
              >
                {typingText || (
                  <span className={styles.typingDots}>
                    <span />
                    <span />
                    <span />
                  </span>
                )}
                <span className={styles.cursor} />
              </div>
            </div>
          )}
        </div>

        {/* ── Input bar ── */}
        <div className={styles.mockInput}>
          <span className={styles.mockInputPlaceholder}>
            {isTyping === "user" ? typingText : "Message…"}
          </span>
          <div className={`${styles.mockSend} ${isTyping === "user" ? styles.mockSendPulse : ""}`}>
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>

        {/* ── Lead captured banner ── */}
        {leadCaptured && (
          <div className={styles.leadBanner}>
            <span className={styles.leadBannerIcon}>🎯</span>
            <span>Lead → CRM</span>
          </div>
        )}
      </div>
    </div>
  );
}
