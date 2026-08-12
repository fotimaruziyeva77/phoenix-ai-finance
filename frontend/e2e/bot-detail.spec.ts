import { expect, test } from "@playwright/test";

import { seedAuthSession } from "./helpers/auth-storage";

const DEFAULT_BOT_AI_FIELDS = {
  provider_name: "gemini",
  model_name: null as string | null,
  temperature: null as number | null,
  max_output_tokens: null as number | null,
};

async function seedDetailSession(page: import("@playwright/test").Page) {
  await seedAuthSession(page, {
    userOverrides: {
      email: "bot-detail-e2e@example.com",
      full_name: "Bot Detail E2E",
    },
    accessToken: "detail-test-token",
    refreshToken: "detail-test-refresh",
  });
}

/** Matches GET /conversations/{id} shape (no client-side defaults). */
function conversationRow(
  overrides: Record<string, unknown> & { id: string; bot_id: string; owner_id: string; created_at: string; updated_at: string },
) {
  return {
    channel: null,
    status: "active",
    current_state: "start",
    detected_intent: null,
    niche_id_snapshot: "education",
    collected_data_json: {},
    last_user_message_at: null,
    last_assistant_message_at: null,
    ...overrides,
  };
}

test.describe("bot detail page", () => {
  test.beforeEach(async ({ page }) => {
    await seedDetailSession(page);
  });

  test("loads bot info and saves editable core fields", async ({ page }) => {
    const persisted = {
      id: "bot_123",
      owner_id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Sales Bot",
      niche_id: "education",
      goal_type: "sales",
      status: "draft",
      welcome_message: "Hello there",
      tone: "friendly",
      language: "en",
      short_description: "Lead qualification",
      ...DEFAULT_BOT_AI_FIELDS,
      created_at: "2026-03-01T12:00:00.000Z",
      updated_at: "2026-03-01T12:00:00.000Z",
    };

    const convId = "cccccccc-cccc-4ccc-cccc-cccccccccccc";

    await page.route("**/api/v1/bots/bot_123**", async (route) => {
      const method = route.request().method();
      const path = new URL(route.request().url()).pathname;

      if (path.endsWith("/chat/test") && method === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation_id: convId,
            user_message_id: "uuuuuuuu-uuuu-4uuu-uuuu-uuuuuuuuuuuu",
            assistant_message_id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
            assistant_text: "E2E stub reply",
            model_name: "stub-model",
            latency_ms: 12,
            tokens_input: 1,
            tokens_output: 2,
            tokens_total: 3,
            cost_usd: "0.000001",
          }),
        });
        return;
      }

      if (path.includes("/conversations/") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation: conversationRow({
              id: convId,
              bot_id: "bot_123",
              owner_id: "550e8400-e29b-41d4-a716-446655440000",
              created_at: "2026-03-01T12:00:00.000Z",
              updated_at: "2026-03-01T12:00:00.000Z",
            }),
            messages: [
              {
                id: "uuuuuuuu-uuuu-4uuu-uuuu-uuuuuuuuuuuu",
                conversation_id: convId,
                bot_id: "bot_123",
                role: "user",
                content: "Hello from e2e",
                tokens_input: null,
                tokens_output: null,
                tokens_total: null,
                latency_ms: null,
                cost_usd: null,
                model_name: null,
                created_at: "2026-03-01T12:00:01.000Z",
              },
              {
                id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
                conversation_id: convId,
                bot_id: "bot_123",
                role: "assistant",
                content: "E2E stub reply",
                tokens_input: 1,
                tokens_output: 2,
                tokens_total: 3,
                latency_ms: 12,
                cost_usd: "0.000001",
                model_name: "stub-model",
                created_at: "2026-03-01T12:00:02.000Z",
              },
            ],
          }),
        });
        return;
      }

      if (path.endsWith("/knowledge/files") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
        return;
      }

      if (path === "/api/v1/bots/bot_123" && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(persisted),
        });
        return;
      }

      if (path === "/api/v1/bots/bot_123" && method === "PATCH") {
        const payload = route.request().postDataJSON() as Record<string, unknown>;
        persisted.name = String(payload.name ?? persisted.name);
        persisted.status =
          (payload.status as "draft" | "active" | "paused" | "archived" | undefined) ?? persisted.status;
        persisted.welcome_message = (payload.welcome_message as string | null | undefined) ?? null;
        persisted.tone = (payload.tone as string | null | undefined) ?? null;
        persisted.language = (payload.language as string | null | undefined) ?? null;
        persisted.short_description = (payload.short_description as string | null | undefined) ?? null;
        if ("model_name" in payload) {
          persisted.model_name = (payload.model_name as string | null | undefined) ?? null;
        }
        if ("temperature" in payload) {
          persisted.temperature = (payload.temperature as number | null | undefined) ?? null;
        }
        if ("max_output_tokens" in payload) {
          persisted.max_output_tokens = (payload.max_output_tokens as number | null | undefined) ?? null;
        }
        persisted.updated_at = "2026-03-02T12:00:00.000Z";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(persisted),
        });
      }
    });

    await page.goto("/dashboard/bots/bot_123");
    await expect(page.getByTestId("bot-detail-page")).toBeVisible();
    await expect(page.getByTestId("bot-test-chat-panel")).toBeVisible();
    await expect(page.getByLabel("Name")).toHaveValue("Sales Bot");
    await expect(page.getByText("Education")).toBeVisible();
    await expect(page.getByText("Sales", { exact: true })).toBeVisible();

    await page.getByLabel("Name").fill("Sales Bot Updated");
    await page.getByLabel("Welcome message").fill("Welcome!");
    await page.getByLabel("Tone").fill("professional");
    await page.getByLabel("Language").fill("es");
    await page.getByLabel("Short description").fill("Updated profile");
    await page.getByLabel("Status").selectOption("active");
    await page.getByTestId("bot-detail-save-btn").click();

    await expect(page.getByTestId("bot-detail-save-success")).toHaveText("Changes saved.");
    await expect(page.getByLabel("Name")).toHaveValue("Sales Bot Updated");
    await expect(page.getByTestId("bot-status-active").first()).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("Name")).toHaveValue("Sales Bot Updated");
    await expect(page.getByLabel("Welcome message")).toHaveValue("Welcome!");
    await expect(page.getByLabel("Language")).toHaveValue("es");
  });

  test("shows error UI when detail load fails", async ({ page }) => {
    await page.route("**/api/v1/bots/bot_404", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "bot_not_found", message: "Bot not found" } }),
      });
    });
    await page.goto("/dashboard/bots/bot_404");
    await expect(page.getByTestId("bot-detail-load-error")).toBeVisible();
    await expect(page.getByText("Bot not found.")).toBeVisible();
  });

  test("shows non-owner access error on detail open", async ({ page }) => {
    await page.route("**/api/v1/bots/bot_forbidden", async (route) => {
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "bot_forbidden", message: "Forbidden" } }),
      });
    });
    await page.goto("/dashboard/bots/bot_forbidden");
    await expect(page.getByTestId("bot-detail-load-error")).toBeVisible();
    await expect(page.getByText("You do not have access to this bot.")).toBeVisible();
  });

  test("shows clean save error when patch fails", async ({ page }) => {
    await page.route("**/api/v1/bots/bot_save_error", async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "bot_save_error",
            owner_id: "550e8400-e29b-41d4-a716-446655440000",
            name: "Error Bot",
            niche_id: "services",
            goal_type: "faq",
            status: "draft",
            welcome_message: null,
            tone: null,
            language: "en",
            short_description: null,
            ...DEFAULT_BOT_AI_FIELDS,
            created_at: "2026-03-01T12:00:00.000Z",
            updated_at: "2026-03-01T12:00:00.000Z",
          }),
        });
        return;
      }
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "bot_validation_error", message: "name is invalid" } }),
      });
    });

    await page.goto("/dashboard/bots/bot_save_error");
    await page.getByLabel("Name").fill("Error Bot Updated");
    await page.getByTestId("bot-detail-save-btn").click();
    await expect(page.getByTestId("bot-detail-save-error")).toHaveText("name is invalid");
  });

  test("archive action requires confirmation and updates status cleanly", async ({ page }) => {
    await page.route("**/api/v1/bots/**", async (route) => {
      const method = route.request().method();
      const url = route.request().url();
      if (!url.includes("/api/v1/bots/bot_archive")) {
        await route.continue();
        return;
      }
      if (method === "OPTIONS") {
        await route.fulfill({
          status: 204,
          headers: {
            "access-control-allow-origin": "*",
            "access-control-allow-methods": "GET,POST,PATCH,OPTIONS",
            "access-control-allow-headers": "authorization,content-type",
          },
          body: "",
        });
        return;
      }
      if (method === "GET") {
        const path = new URL(url).pathname;
        if (path.endsWith("/knowledge/files")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ items: [], total: 0 }),
          });
          return;
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "bot_archive",
            owner_id: "550e8400-e29b-41d4-a716-446655440000",
            name: "Archive Candidate",
            niche_id: "services",
            goal_type: "support",
            status: "active",
            welcome_message: null,
            tone: null,
            language: "en",
            short_description: null,
            ...DEFAULT_BOT_AI_FIELDS,
            created_at: "2026-03-01T12:00:00.000Z",
            updated_at: "2026-03-01T12:00:00.000Z",
          }),
        });
        return;
      }
      if (method === "POST" && url.includes("/archive")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "bot_archive",
            owner_id: "550e8400-e29b-41d4-a716-446655440000",
            name: "Archive Candidate",
            niche_id: "services",
            goal_type: "support",
            status: "archived",
            welcome_message: null,
            tone: null,
            language: "en",
            short_description: null,
            ...DEFAULT_BOT_AI_FIELDS,
            created_at: "2026-03-01T12:00:00.000Z",
            updated_at: "2026-03-02T12:00:00.000Z",
          }),
        });
        return;
      }
      await route.continue();
    });
    await page.goto("/dashboard/bots/bot_archive");
    await page.getByTestId("bot-detail-archive-btn").click();
    await expect(page.getByTestId("bot-detail-archive-confirm-btn")).toBeVisible();
    await page.getByTestId("bot-detail-archive-confirm-btn").click();
    await expect(page.getByTestId("bot-detail-save-success")).toContainText("Bot archived");
    await expect(page.getByTestId("bot-status-archived").first()).toBeVisible();
    await expect(page.getByTestId("bot-detail-archive-btn")).toHaveText("Already archived");
    await expect(page.getByTestId("bot-test-chat-archived-notice")).toBeVisible();
  });

  test("test chat sends message and shows assistant reply from API", async ({ page }) => {
    const convId = "dddddddd-dddd-4ddd-dddd-dddddddddddd";
    const persisted = {
      id: "bot_tc",
      owner_id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Chat Flow Bot",
      niche_id: "education",
      goal_type: "support",
      status: "draft",
      welcome_message: null,
      tone: null,
      language: "en",
      short_description: null,
      ...DEFAULT_BOT_AI_FIELDS,
      created_at: "2026-03-01T12:00:00.000Z",
      updated_at: "2026-03-01T12:00:00.000Z",
    };

    await page.route("**/api/v1/bots/bot_tc**", async (route) => {
      const method = route.request().method();
      const path = new URL(route.request().url()).pathname;

      if (path.endsWith("/chat/test") && method === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation_id: convId,
            user_message_id: "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee",
            assistant_message_id: "ffffffff-ffff-4fff-ffff-ffffffffffff",
            assistant_text: "Stub assistant for e2e",
            model_name: "stub-model",
            latency_ms: 8,
            tokens_input: 2,
            tokens_output: 4,
            tokens_total: 6,
            cost_usd: "0.000002",
          }),
        });
        return;
      }

      if (path.includes("/conversations/") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation: conversationRow({
              id: convId,
              bot_id: "bot_tc",
              owner_id: "550e8400-e29b-41d4-a716-446655440000",
              niche_id_snapshot: "education",
              created_at: "2026-03-01T12:00:00.000Z",
              updated_at: "2026-03-01T12:00:00.000Z",
            }),
            messages: [
              {
                id: "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee",
                conversation_id: convId,
                bot_id: "bot_tc",
                role: "user",
                content: "Hello from e2e",
                tokens_input: null,
                tokens_output: null,
                tokens_total: null,
                latency_ms: null,
                cost_usd: null,
                model_name: null,
                created_at: "2026-03-01T12:00:01.000Z",
              },
              {
                id: "ffffffff-ffff-4fff-ffff-ffffffffffff",
                conversation_id: convId,
                bot_id: "bot_tc",
                role: "assistant",
                content: "Stub assistant for e2e",
                tokens_input: 2,
                tokens_output: 4,
                tokens_total: 6,
                latency_ms: 8,
                cost_usd: "0.000002",
                model_name: "stub-model",
                created_at: "2026-03-01T12:00:02.000Z",
              },
            ],
          }),
        });
        return;
      }

      if (path.endsWith("/knowledge/files") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
        return;
      }

      if (path === "/api/v1/bots/bot_tc" && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(persisted),
        });
      }
    });

    await page.goto("/dashboard/bots/bot_tc");
    await expect(page.getByTestId("bot-test-chat-panel")).toBeVisible();
    await page.getByLabel("Test chat message").fill("Hello from e2e");
    await page.getByTestId("chat-composer-send").click();
    await expect(page.getByText("Stub assistant for e2e")).toBeVisible();
    await expect(page.getByTestId("admin-reply-meta")).toContainText("stub-model");
  });

  test("test chat multi-turn reuses thread and shows API-driven conversation snapshot", async ({ page }) => {
    const convId = "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee";
    const postBodies: Array<{ message?: string; conversation_id?: string }> = [];
    let getTranscriptCalls = 0;

    const persisted = {
      id: "bot_mt",
      owner_id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Multi-turn Bot",
      niche_id: "education",
      goal_type: "sales",
      status: "draft",
      welcome_message: null,
      tone: null,
      language: "en",
      short_description: null,
      ...DEFAULT_BOT_AI_FIELDS,
      created_at: "2026-03-01T12:00:00.000Z",
      updated_at: "2026-03-01T12:00:00.000Z",
    };

    await page.route("**/api/v1/bots/bot_mt**", async (route) => {
      const method = route.request().method();
      const path = new URL(route.request().url()).pathname;

      if (path.endsWith("/chat/test") && method === "POST") {
        const body = route.request().postDataJSON() as { message?: string; conversation_id?: string };
        postBodies.push(body);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation_id: convId,
            user_message_id: "11111111-1111-4111-8111-111111111111",
            assistant_message_id: "22222222-2222-4222-8222-222222222222",
            assistant_text:
              postBodies.length === 1
                ? "First turn — what grade is the student?"
                : "Second turn — which subject?",
            model_name: "stub-model",
            latency_ms: 5,
            tokens_input: 1,
            tokens_output: 2,
            tokens_total: 3,
            cost_usd: "0.000001",
          }),
        });
        return;
      }

      if (path.includes("/conversations/") && method === "GET") {
        getTranscriptCalls += 1;
        const u1 = {
          id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
          conversation_id: convId,
          bot_id: "bot_mt",
          role: "user",
          content: "Turn one message",
          tokens_input: null,
          tokens_output: null,
          tokens_total: null,
          latency_ms: null,
          cost_usd: null,
          model_name: null,
          created_at: "2026-03-01T12:00:01.000Z",
        };
        const a1 = {
          id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
          conversation_id: convId,
          bot_id: "bot_mt",
          role: "assistant",
          content: "First turn — what grade is the student?",
          tokens_input: 1,
          tokens_output: 2,
          tokens_total: 3,
          latency_ms: 5,
          cost_usd: "0.000001",
          model_name: "stub-model",
          created_at: "2026-03-01T12:00:02.000Z",
        };
        const u2 = {
          id: "cccccccc-cccc-4ccc-cccc-cccccccccccc",
          conversation_id: convId,
          bot_id: "bot_mt",
          role: "user",
          content: "Turn two message",
          tokens_input: null,
          tokens_output: null,
          tokens_total: null,
          latency_ms: null,
          cost_usd: null,
          model_name: null,
          created_at: "2026-03-01T12:00:03.000Z",
        };
        const a2 = {
          id: "dddddddd-dddd-4ddd-dddd-dddddddddddd",
          conversation_id: convId,
          bot_id: "bot_mt",
          role: "assistant",
          content: "Second turn — which subject?",
          tokens_input: 1,
          tokens_output: 2,
          tokens_total: 3,
          latency_ms: 5,
          cost_usd: "0.000001",
          model_name: "stub-model",
          created_at: "2026-03-01T12:00:04.000Z",
        };

        if (getTranscriptCalls === 1) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              conversation: conversationRow({
                id: convId,
                bot_id: "bot_mt",
                owner_id: "550e8400-e29b-41d4-a716-446655440000",
                current_state: "start",
                collected_data_json: {},
                created_at: "2026-03-01T12:00:00.000Z",
                updated_at: "2026-03-01T12:00:02.000Z",
              }),
              messages: [u1, a1],
            }),
          });
          return;
        }

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation: conversationRow({
              id: convId,
              bot_id: "bot_mt",
              owner_id: "550e8400-e29b-41d4-a716-446655440000",
              current_state: "qualification",
              detected_intent: "sales_interest",
              collected_data_json: { student_grade: "Grade 9", __orch_target_field: "subject" },
              created_at: "2026-03-01T12:00:00.000Z",
              updated_at: "2026-03-01T12:00:04.000Z",
            }),
            messages: [u1, a1, u2, a2],
          }),
        });
        return;
      }

      if (path.endsWith("/knowledge/files") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
        return;
      }

      if (path === "/api/v1/bots/bot_mt" && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(persisted),
        });
      }
    });

    await page.goto("/dashboard/bots/bot_mt");
    await expect(page.getByTestId("bot-test-chat-panel")).toBeVisible();

    await page.getByLabel("Test chat message").fill("Turn one message");
    await page.getByTestId("chat-composer-send").click();
    await expect(page.getByText("First turn — what grade is the student?")).toBeVisible();
    await expect(page.getByTestId("bot-test-chat-current-state")).toHaveText("start");

    await page.getByLabel("Test chat message").fill("Turn two message");
    await page.getByTestId("chat-composer-send").click();
    await expect(page.getByText("Second turn — which subject?")).toBeVisible();

    expect(postBodies.length).toBe(2);
    expect(postBodies[0].conversation_id == null).toBe(true);
    expect(postBodies[1].conversation_id).toBe(convId);

    await expect(page.getByTestId("bot-test-chat-current-state")).toHaveText("qualification");
    await expect(page.getByTestId("bot-test-chat-collected-fields")).toContainText("Grade 9");
    await expect(page.getByTestId("bot-test-chat-collected-json")).toContainText("student_grade");
  });

  test("test chat keeps error visible and transcript after failed send on existing thread", async ({ page }) => {
    const convId = "ffffffff-ffff-4fff-ffff-ffffffffffff";
    let postCount = 0;

    const persisted = {
      id: "bot_err",
      owner_id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Error Thread Bot",
      niche_id: "education",
      goal_type: "sales",
      status: "draft",
      welcome_message: null,
      tone: null,
      language: "en",
      short_description: null,
      ...DEFAULT_BOT_AI_FIELDS,
      created_at: "2026-03-01T12:00:00.000Z",
      updated_at: "2026-03-01T12:00:00.000Z",
    };

    await page.route("**/api/v1/bots/bot_err**", async (route) => {
      const method = route.request().method();
      const path = new URL(route.request().url()).pathname;

      if (path === "/api/v1/bots/bot_err" && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(persisted),
        });
        return;
      }

      if (path.endsWith("/knowledge/files") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
        return;
      }

      if (path.endsWith("/chat/test") && method === "POST") {
        postCount += 1;
        if (postCount === 1) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              conversation_id: convId,
              user_message_id: "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee",
              assistant_message_id: "dddddddd-dddd-4ddd-dddd-dddddddddddd",
              assistant_text: "First reply ok",
              model_name: "stub-model",
              latency_ms: 2,
              tokens_input: 1,
              tokens_output: 1,
              tokens_total: 2,
              cost_usd: "0.000001",
            }),
          });
          return;
        }
        await route.fulfill({
          status: 502,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "ai_inference_failed",
              message: "Model provider unavailable for this turn.",
            },
          }),
        });
        return;
      }

      if (path.includes("/conversations/") && method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            conversation: conversationRow({
              id: convId,
              bot_id: "bot_err",
              owner_id: "550e8400-e29b-41d4-a716-446655440000",
              current_state: "qualification",
              detected_intent: "sales_interest",
              collected_data_json: { student_grade: "Grade 8" },
              created_at: "2026-03-01T12:00:00.000Z",
              updated_at: "2026-03-01T12:00:02.000Z",
            }),
            messages: [
              {
                id: "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee",
                conversation_id: convId,
                bot_id: "bot_err",
                role: "user",
                content: "first line",
                tokens_input: null,
                tokens_output: null,
                tokens_total: null,
                latency_ms: null,
                cost_usd: null,
                model_name: null,
                created_at: "2026-03-01T12:00:01.000Z",
              },
              {
                id: "dddddddd-dddd-4ddd-dddd-dddddddddddd",
                conversation_id: convId,
                bot_id: "bot_err",
                role: "assistant",
                content: "First reply ok",
                tokens_input: 1,
                tokens_output: 1,
                tokens_total: 2,
                latency_ms: 2,
                cost_usd: "0.000001",
                model_name: "stub-model",
                created_at: "2026-03-01T12:00:02.000Z",
              },
            ],
          }),
        });
        return;
      }
    });

    await page.goto("/dashboard/bots/bot_err");
    await expect(page.getByTestId("bot-test-chat-panel")).toBeVisible();

    await page.getByLabel("Test chat message").fill("first line");
    await page.getByTestId("chat-composer-send").click();
    await expect(page.getByText("First reply ok")).toBeVisible();

    await page.getByLabel("Test chat message").fill("second line fails");
    await page.getByTestId("chat-composer-send").click();

    const banner = page.getByTestId("bot-test-chat-error");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Model provider unavailable");
    await expect(banner).not.toContainText("Traceback");

    await expect(page.getByText("First reply ok")).toBeVisible();
    await expect(page.getByTestId("bot-test-chat-collected-fields")).toContainText("Grade 8");
  });
});
