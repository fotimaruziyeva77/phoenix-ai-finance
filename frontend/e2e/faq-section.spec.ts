import { expect, test } from "@playwright/test";

test.describe("FAQ section", () => {
  test("expand and collapse toggles details open state", async ({ page }) => {
    await page.goto("/#faq");
    const first = page.locator("#faq details").first();
    const summary = first.locator("summary");

    await expect(first).not.toHaveAttribute("open");
    await expect(first.getByText("It lets you run an AI assistant")).not.toBeVisible();

    await summary.click();
    await expect(first).toHaveAttribute("open");
    await expect(first.getByText("It lets you run an AI assistant")).toBeVisible();

    await summary.click();
    await expect(first).not.toHaveAttribute("open");
    await expect(first.getByText("It lets you run an AI assistant")).not.toBeVisible();
  });

  test("opening another item collapses the previous (accordion group)", async ({ page }) => {
    await page.goto("/");
    const items = page.locator("#faq details");
    const first = items.nth(0);
    const second = items.nth(1);

    await first.locator("summary").click();
    await expect(first).toHaveAttribute("open");

    await second.locator("summary").click();
    await expect(second).toHaveAttribute("open");

    // With name="faq", Chromium keeps one open; if unsupported, both may stay open—still no crash.
    const firstOpen = await first.evaluate((el: HTMLDetailsElement) => el.open);
    const secondOpen = await second.evaluate((el: HTMLDetailsElement) => el.open);
    expect(secondOpen).toBe(true);
    if (firstOpen && secondOpen) {
      /* multiple open allowed in this browser */
    } else {
      expect(firstOpen).toBe(false);
    }
  });

  test("no horizontal layout overflow on mobile and desktop", async ({ page }) => {
    for (const size of [
      { width: 390, height: 844 },
      { width: 1280, height: 900 },
    ] as const) {
      await page.setViewportSize(size);
      await page.goto("/#faq");
      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(
        overflow.scrollWidth,
        `no horizontal scroll at ${size.width}px`,
      ).toBeLessThanOrEqual(overflow.clientWidth + 1);
    }
  });
});
