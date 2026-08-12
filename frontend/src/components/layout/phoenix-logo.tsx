/**
 * Phoenix AI brand mark.
 *
 * A rising phoenix enclosed by a ring, with a growth bar-chart forming its tail —
 * "g'oyadan o'sishgacha". Drawn as inline SVG rather than a raster so it stays
 * crisp at every size and inherits theme colours (the CSP on published pages also
 * blocks external image hosts).
 */

type Props = {
  className?: string;
  style?: React.CSSProperties;
  /** Mark only, without the wordmark — for compact placements. */
  markOnly?: boolean;
  showTagline?: boolean;
  taglineText?: string;
};

export function PhoenixLogo({
  className,
  style,
  markOnly = false,
  showTagline = false,
  taglineText = "G'oyadan — o'sishgacha",
}: Props) {
  if (markOnly) {
    return (
      <svg
        className={className}
        style={style}
        viewBox="0 0 64 64"
        fill="none"
        aria-hidden
        focusable="false"
      >
        <PhoenixMark />
      </svg>
    );
  }

  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
      <svg
        viewBox="0 0 64 64"
        fill="none"
        aria-hidden
        focusable="false"
        style={{ width: "2rem", height: "2rem", flex: "none" }}
      >
        <PhoenixMark />
      </svg>
      <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.05 }}>
        <span
          style={{
            fontFamily: "var(--font-display), system-ui, sans-serif",
            fontWeight: 500,
            letterSpacing: "0.01em",
            fontSize: "0.9375rem",
          }}
        >
          PHOENIX <span style={{ color: "var(--bf-accent, #3bc98a)" }}>AI</span>
        </span>
        {showTagline ? (
          <span
            style={{
              fontSize: "0.5625rem",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              opacity: 0.62,
            }}
          >
            {taglineText}
          </span>
        ) : null}
      </span>
    </span>
  );
}

function PhoenixMark() {
  return (
    <>
      <defs>
        <linearGradient id="pxGrowth" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#2f7d5f" />
          <stop offset="100%" stopColor="#7fe0b0" />
        </linearGradient>
        <linearGradient id="pxBird" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#94a3b8" />
          <stop offset="100%" stopColor="#e2e8f0" />
        </linearGradient>
      </defs>

      {/* enclosing ring, open at the lower right where the chart rises out */}
      <path
        d="M32 4a28 28 0 1 0 26.4 37.4"
        stroke="url(#pxBird)"
        strokeWidth="2.6"
        strokeLinecap="round"
        opacity="0.55"
        fill="none"
      />

      {/* rising phoenix: head, beak, curved wing sweep */}
      <path
        d="M30.5 15.5c2.6-3.4 6.6-5.2 10.7-4.6-1.5 1.2-2.4 2.6-2.8 4.3 2.1-.4 4 .1 5.6 1.4-2 .4-3.5 1.4-4.6 2.9"
        fill="url(#pxBird)"
      />
      <path
        d="M39.4 19.6c-3.9 1-7 3.2-9.4 6.4-2.6 3.5-3.8 7.5-3.6 11.9-3.7-3.1-6.1-6.9-7.2-11.4-.8 5.6.6 10.6 4.2 15-4.4-1.3-7.9-3.9-10.4-7.9.9 8.4 5.6 14.4 13.9 17.6"
        stroke="url(#pxBird)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* growth bars — the tail */}
      <rect x="33" y="43" width="4.4" height="9" rx="1.2" fill="url(#pxGrowth)" opacity="0.75" />
      <rect x="40" y="37" width="4.4" height="15" rx="1.2" fill="url(#pxGrowth)" opacity="0.88" />
      <rect x="47" y="30" width="4.4" height="22" rx="1.2" fill="url(#pxGrowth)" />
    </>
  );
}
