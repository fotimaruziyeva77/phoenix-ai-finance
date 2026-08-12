"use client";

type Props = {
  error: Error;
  onReset: () => void;
};

export function ErrorFallback({ error, onReset }: Props) {
  return (
    <div
      role="alert"
      style={{
        padding: "1.5rem",
        maxWidth: "32rem",
        margin: "2rem auto",
        border: "1px solid color-mix(in srgb, CanvasText 20%, transparent)",
        borderRadius: "8px",
      }}
    >
      <h2 style={{ marginTop: 0 }}>Something went wrong</h2>
      <p style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
        {error.message}
      </p>
      <button type="button" onClick={onReset}>
        Try again
      </button>
    </div>
  );
}
