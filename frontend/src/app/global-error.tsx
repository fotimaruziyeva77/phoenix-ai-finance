"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <h2 style={{ fontFamily: "system-ui, sans-serif", padding: "1.5rem" }}>
          Application error
        </h2>
        <p style={{ fontFamily: "monospace", padding: "0 1.5rem" }}>
          {error.message}
        </p>
        <button
          type="button"
          style={{ margin: "1rem 1.5rem" }}
          onClick={() => reset()}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
