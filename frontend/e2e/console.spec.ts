import { expect, test } from "@playwright/test";

/**
 * Fails if the browser reports console.error or uncaught page errors on key routes.
 */
test.describe("no console errors", () => {
  test("home, login, signup load without console errors or page errors", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });
    page.on("pageerror", (err) => {
      pageErrors.push(err.message);
    });

    for (const path of ["/", "/login", "/signup"] as const) {
      await page.goto(path);
      await page.waitForLoadState("load");
    }

    expect(pageErrors, `page errors: ${pageErrors.join(" | ")}`).toEqual([]);
    expect(
      consoleErrors,
      `console errors: ${consoleErrors.join(" | ")}`,
    ).toEqual([]);
  });
});
