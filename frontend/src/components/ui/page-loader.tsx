export function PageLoader() {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "40vh",
        gap: "0.75rem",
      }}
    >
      <span
        style={{
          width: "1.5rem",
          height: "1.5rem",
          border: "2px solid color-mix(in srgb, CanvasText 25%, transparent)",
          borderTopColor: "CanvasText",
          borderRadius: "50%",
          animation: "spin 0.7s linear infinite",
        }}
      />
      <span>Loading…</span>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
