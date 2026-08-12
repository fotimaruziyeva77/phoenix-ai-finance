import { fireEvent, render, screen, waitFor, within } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WidgetApp } from "./WidgetApp";
import { errJson, okJson } from "./test/fetchMocks";

const API = "http://test.local:9999";

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

function bootstrapPayload(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    is_enabled: true,
    welcome_text: "Welcome from API",
    theme: null,
    bot_display_name: "Sales Bot",
    ...overrides,
  };
}

function chatPayload(assistantText: string) {
  return {
    conversation_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    visitor_session_key: "visitor-key-16chars",
    user_message_id: "uuuuuuuu-uuuu-4uuu-8uuu-uuuuuuuuuuuu",
    assistant_message_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    assistant_text: assistantText,
    bot_display_name: "Sales Bot",
  };
}

describe("WidgetApp", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("opens and closes the panel (launcher + header close)", async () => {
    fetchMock.mockResolvedValue(okJson(bootstrapPayload()));

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-open-close" apiBaseUrl={API} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /open chat/i }));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /close chat panel/i }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("loads bootstrap from the public API when the panel opens", async () => {
    fetchMock.mockResolvedValue(okJson(bootstrapPayload({ welcome_text: "Hi there" })));

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-bootstrap" apiBaseUrl={API} />);

    await user.click(screen.getByRole("button", { name: /open chat/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API}/api/v1/public/widget/pk-bootstrap/bootstrap`,
        expect.objectContaining({ method: "GET" }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Hi there")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Sales Bot" })).toBeInTheDocument();
    });
  });

  it("shows bootstrap loading then content", async () => {
    let resolveJson!: (v: unknown) => void;
    const jsonPromise = new Promise((resolve) => {
      resolveJson = resolve;
    });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => jsonPromise,
    } as Response);

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-loading" apiBaseUrl={API} />);
    await user.click(screen.getByRole("button", { name: /open chat/i }));

    expect(await screen.findByText(/Connecting/i)).toBeInTheDocument();

    resolveJson!(bootstrapPayload({ welcome_text: "Loaded" }));

    await waitFor(() => {
      expect(screen.queryByText(/Connecting/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText("Loaded")).toBeInTheDocument();
  });

  it("shows bootstrap error state on API failure", async () => {
    fetchMock.mockResolvedValue(
      errJson(403, { error: { code: "widget_origin_forbidden", message: "Origin blocked." } }),
    );

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-err-boot" apiBaseUrl={API} />);
    await user.click(screen.getByRole("button", { name: /open chat/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Origin blocked.");
    });
  });

  it("sends chat to the public API and renders user + assistant messages from the response", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.includes("/bootstrap")) return okJson(bootstrapPayload({ welcome_text: null }));
      if (url.includes("/chat")) return okJson(chatPayload("Reply from model"));
      throw new Error(`unexpected fetch: ${url}`);
    });

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-chat" apiBaseUrl={API} />);
    await user.click(screen.getByRole("button", { name: /open chat/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sales Bot" })).toBeInTheDocument();
    });

    const uniqueUserLine = `hello-${Date.now()}`;
    await user.type(screen.getByRole("textbox", { name: /message/i }), uniqueUserLine);
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    await waitFor(() => {
      const chatCall = fetchMock.mock.calls.find((c) => requestUrl(c[0] as RequestInfo).includes("/chat"));
      expect(chatCall).toBeDefined();
      expect(chatCall![1]).toEqual(
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
      const body = JSON.parse((chatCall![1] as RequestInit).body as string);
      expect(body.message).toBe(uniqueUserLine);
    });

    await waitFor(() => {
      expect(screen.getByText("Reply from model")).toBeInTheDocument();
    });

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(uniqueUserLine)).toBeInTheDocument();
  });

  it("does not show assistant transcript until the chat API succeeds (no fake replies)", async () => {
    fetchMock.mockResolvedValueOnce(okJson(bootstrapPayload()));

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-no-fake" apiBaseUrl={API} />);
    await user.click(screen.getByRole("button", { name: /open chat/i }));

    await waitFor(() => screen.getByText("Welcome from API"));

    expect(screen.queryByText("Synthetic assistant")).not.toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Assistant" })).not.toBeInTheDocument();
  });

  it("shows sending state while chat request is in flight", async () => {
    let resolveChat!: (v: unknown) => void;
    const chatJson = new Promise((resolve) => {
      resolveChat = resolve;
    });
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes("/bootstrap")) return okJson(bootstrapPayload({ welcome_text: null }));
      if (url.includes("/chat")) {
        return {
          ok: true,
          status: 200,
          json: () => chatJson,
        } as Response;
      }
      throw new Error(`unexpected fetch: ${url}`);
    });

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-sending" apiBaseUrl={API} />);
    await user.click(screen.getByRole("button", { name: /open chat/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sales Bot" })).toBeInTheDocument();
    });

    const box = screen.getByRole("textbox", { name: /message/i });
    fireEvent.input(box, { target: { value: "wait" } });
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText(/Sending/i)).toBeInTheDocument();

    resolveChat!(chatPayload("done"));

    await waitFor(() => {
      expect(screen.queryByText(/Sending/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText("done")).toBeInTheDocument();
  });

  it("shows send error when chat API fails", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes("/bootstrap")) return okJson(bootstrapPayload({ welcome_text: null }));
      if (url.includes("/chat")) {
        return errJson(429, {
          error: { code: "rate_limit_exceeded", message: "Too many messages." },
        });
      }
      throw new Error(`unexpected fetch: ${url}`);
    });

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-send-err" apiBaseUrl={API} />);
    await user.click(screen.getByRole("button", { name: /open chat/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sales Bot" })).toBeInTheDocument();
    });

    const box = screen.getByRole("textbox", { name: /message/i });
    fireEvent.input(box, { target: { value: "hello" } });
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      expect(alerts.some((el) => el.textContent?.includes("Too many messages"))).toBe(true);
    });
  });
});

describe("widget integration smoke", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("full flow: open → bootstrap → type → send → assistant visible", async () => {
    const assistantLine = "Smoke assistant line";
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes("/bootstrap")) return okJson(bootstrapPayload());
      if (url.includes("/chat")) return okJson(chatPayload(assistantLine));
      throw new Error(`unexpected fetch: ${url}`);
    });

    const user = userEvent.setup();
    render(<WidgetApp publicKey="pk-smoke" apiBaseUrl={API} />);

    await user.click(screen.getByRole("button", { name: /open chat/i }));
    await waitFor(() => expect(screen.getByText("Welcome from API")).toBeInTheDocument());

    await user.type(screen.getByRole("textbox", { name: /message/i }), "smoke test");
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    await waitFor(() => expect(screen.getByText(assistantLine)).toBeInTheDocument());
    expect(screen.getByText("smoke test")).toBeInTheDocument();
  });
});
